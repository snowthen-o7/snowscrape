import boto3
import json
import os
import requests
import time

from botocore.exceptions import ClientError
from connection_pool import get_table, get_cached_session_data, set_cached_session_data, get_http_session, close_http_session
from crawl_manager import process_queries
from datetime import datetime, timezone
from logger import get_logger, log_exception
from metrics import get_metrics_emitter
from typing import Any, Dict
from utils import decimal_to_float, delete_job_links, fetch_url_with_session, fetch_urls_for_job, initialize_session, parse_links_from_file, save_results_to_s3, save_session_data, update_job_status, update_url_status, validate_job_data
from webhook_dispatcher import WebhookDispatcher

# Initialize logger and metrics
logger = get_logger(__name__)
metrics = get_metrics_emitter()

# Use connection pool for DynamoDB tables
job_table = get_table(os.environ['DYNAMODB_JOBS_TABLE'])
url_table = get_table(os.environ['DYNAMODB_URLS_TABLE'])

# Create a new job in DynamoDB
def create_job(job_data):
	try:
		# Parse the list of URLs from the external source
		logger.info("Parsing source file for URLs", source=job_data['source'])
		links = parse_links_from_file(job_data['file_mapping'], job_data['source'])
		logger.info("URLs parsed successfully", url_count=len(links))

		# Assign a job_id if it doesn't exist
		job_id = job_data.get('job_id')
		if not job_id:
			import uuid
			job_data['job_id'] = str(uuid.uuid4())
			logger.debug("Generated job_id", job_id=job_data['job_id'])

		# Ensure all necessary fields are present in job_data and add defaults if needed
		job_item = {
			'created_at': job_data.get('created_at', datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
			'file_mapping': job_data['file_mapping'],
			'job_id': job_data['job_id'],
			'last_run': None,
			'link_count': len(links),
			'name': job_data['name'],
			'queries': job_data['queries'],
			'rate_limit': job_data['rate_limit'],
			'results_s3_key': None,
			'scheduling': job_data.get('scheduling', None),
			'source': job_data['source'],
			'status': job_data.get('status', 'ready'),  # Default job status
			'user_id': job_data['user_id'],
			'proxy_config': job_data.get('proxy_config', {
				'enabled': False,
				'geo_targeting': 'any',
				'rotation_strategy': 'random',
				'max_retries': 3,
				'fallback_to_direct': True
			}),
			'render_config': job_data.get('render_config', {
				'enabled': False,
				'wait_strategy': 'networkidle',
				'wait_timeout_ms': 30000,
				'wait_for_selector': None,
				'capture_screenshot': False,
				'screenshot_full_page': False,
				'block_resources': [],
				'fallback_to_standard': True
			}),
		}

		# Insert job data into DynamoDB
		logger.info("Creating job in DynamoDB", job_id=job_data['job_id'], job_name=job_data['name'])
		response = job_table.put_item(Item=job_item)
		logger.debug("Job created in DynamoDB", job_id=job_data['job_id'])

  	# Insert URLs into the URL tracking table with state 'ready' (using batch writer for performance)
		logger.info("Inserting URLs into tracking table", job_id=job_data['job_id'], url_count=len(links))
		timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

		# Use batch_writer for efficient bulk inserts (up to 25 items per batch)
		with url_table.batch_writer() as batch:
			for url in links:
				batch.put_item(Item={
					'job_id': job_data['job_id'],
					'url': url,
					'state': 'ready',
					'last_updated': timestamp
				})

		logger.info("Job created successfully", job_id=job_data['job_id'], url_count=len(links))

		# Dispatch job.created webhook event
		try:
			WebhookDispatcher.dispatch_job_created(
				job_id=job_data['job_id'],
				user_id=job_data['user_id'],
				job_data=job_item
			)
		except Exception as e:
			logger.warning("Failed to dispatch job.created webhook", error=str(e))

		return job_data['job_id']

	except ValueError as e:
		log_exception(logger, "Job validation failed", e, job_name=job_data.get('name'))
		return None
	except ClientError as e:
		log_exception(logger, "DynamoDB error creating job", e, job_name=job_data.get('name'))
		return None
	except Exception as e:
		log_exception(logger, "Unexpected error creating job", e, job_name=job_data.get('name'))
		return None

# Delete a job and its related links from DynamoDB
def delete_job(job_id):
	try:
		# 1. Delete all links associated with the job in the url_table
		delete_job_links(job_id)
		
		# 2. Delete the job from the job_table
		job_table.delete_item(Key={'job_id': job_id})
		
		return f"Job {job_id} and related links deleted successfully."
	
	except ClientError as e:
		print(f"Error deleting job: {e.response['Error']['Message']}")
		return None

# Retrieve all job statuses
def get_all_jobs(limit=None, last_evaluated_key=None, projection=None):
	"""
	Retrieve all jobs with pagination support and projection optimization.

	Args:
		limit: Maximum number of items to return
		last_evaluated_key: Key to continue pagination from
		projection: List of attributes to retrieve (reduces data transfer)

	Returns:
		Dictionary with 'items' and optionally 'last_evaluated_key'
	"""
	try:
		scan_params = {}

		# Add projection expression to fetch only needed fields
		if projection:
			scan_params['ProjectionExpression'] = ', '.join(projection)
		else:
			# Default projection for list views (exclude large fields)
			scan_params['ProjectionExpression'] = 'job_id, #name, #status, created_at, last_run, link_count, user_id'
			scan_params['ExpressionAttributeNames'] = {
				'#name': 'name',
				'#status': 'status'
			}

		# Add pagination
		if limit:
			scan_params['Limit'] = limit

		if last_evaluated_key:
			scan_params['ExclusiveStartKey'] = last_evaluated_key

		response = job_table.scan(**scan_params)
		logger.info("Retrieved jobs", count=len(response.get('Items', [])))

		jobs = response.get('Items', [])
		jobs_cleaned = decimal_to_float(jobs)

		result = {'items': jobs_cleaned}

		# Include pagination key if there are more results
		if 'LastEvaluatedKey' in response:
			result['last_evaluated_key'] = response['LastEvaluatedKey']

		return result
	except ClientError as e:
		log_exception(logger, "Error retrieving jobs", e)
		return {'items': []}

# Retrieve details of a specific job
def get_job(job_id):
	try:
		response = job_table.get_item(Key={'job_id': job_id})
		print(f"Retrieved job response: {response}")
		response_cleaned = decimal_to_float(response)
		print(f"Cleaned job response: {response_cleaned}")
		return response_cleaned.get('Item')
	except ClientError as e:
		print(f"Error retrieving job {job_id}: {e.response['Error']['Message']}")
		return None

# Retrieve all crawls for a specific job
def get_job_crawls(job_id):
	try:
		response = job_table.query(
			IndexName='job_id-index',  # Assuming there's a GSI on job_id
			KeyConditionExpression='job_id = :jid',
			ExpressionAttributeValues={':jid': job_id}
		)
		return response.get('Items', [])
	except ClientError as e:
		print(f"Error retrieving crawls for job {job_id}: {e.response['Error']['Message']}")
		return []

# Pause a job (update status to "paused")
def pause_job(job_id):
	try:
		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="set #st = :s",
			ExpressionAttributeNames={'#st': 'status'},
			ExpressionAttributeValues={':s': 'paused'}
		)
		return f"Job {job_id} paused successfully."
	except ClientError as e:
		print(f"Error pausing job: {e.response['Error']['Message']}")
		return None

# Cancel a job (update status to "cancelled")
def cancel_job(job_id):
	"""
	Cancel a job by setting its status to 'cancelled'.
	This will prevent the job from being processed further.

	Args:
		job_id (str): The ID of the job to cancel

	Returns:
		str: Success message, or None on error
	"""
	try:
		# Get job data for webhook dispatch
		response = job_table.get_item(Key={'job_id': job_id})
		job_data = response.get('Item', {})

		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="set #st = :s, cancelled_at = :ct",
			ExpressionAttributeNames={'#st': 'status'},
			ExpressionAttributeValues={
				':s': 'cancelled',
				':ct': datetime.now(timezone.utc).isoformat()
			}
		)

		# Dispatch job.cancelled webhook event
		try:
			WebhookDispatcher.dispatch_job_cancelled(
				job_id=job_id,
				user_id=job_data.get('user_id'),
				job_data=job_data
			)
		except Exception as webhook_error:
			logger.warning("Failed to dispatch job.cancelled webhook", error=str(webhook_error))

		print(f"Job {job_id} cancelled successfully.")
		return f"Job {job_id} cancelled successfully."
	except ClientError as e:
		print(f"Error cancelling job: {e.response['Error']['Message']}")
		return None

def process_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Perform the job by scraping and processing URLs based on the job's queries.

	Args:
	- job_data (dict): The data of the job containing the list of URLs to scrape, queries, etc.

	Returns:
	- dict: A dictionary containing the results of the job, with scraped data for each URL.
	"""
	results = {}
	job_id = job_data['job_id']
	queries = job_data.get('queries', [])  # The list of queries to apply to each URL
	timeout_seconds = job_data.get('timeout', 900)  # Default 15 minutes
	start_time = datetime.now(timezone.utc)

	# Check if job is cancelled before starting
	job = get_job(job_id)
	if job and job.get('status') == 'cancelled':
		print(f"Job {job_id} is cancelled. Skipping processing.")
		return {'status': 'cancelled', 'message': 'Job was cancelled'}

	try:
		# Fetch URLs from the url_table associated with the job
		urls = fetch_urls_for_job(job_id)
		if not urls:
			raise ValueError("No URLs found for the job.")
	except ClientError as e:
		print(f"Error fetching URLs for job {job_id}: {e.response['Error']['Message']}")
		return {'status': 'error', 'message': f"Failed to fetch URLs for job {job_id}"}
	except Exception as e:
		print(f"General error fetching URLs for job {job_id}: {str(e)}")
		return {'status': 'error', 'message': f"General error: {str(e)}"}

	# Initialize progress tracking
	total_urls = len(urls)
	processed_urls = 0
	failed_urls = 0

	# Update job with initial progress
	try:
		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="SET progress = :progress, #status = :status",
			ExpressionAttributeNames={'#status': 'status'},
			ExpressionAttributeValues={
				':progress': {
					'total': total_urls,
					'processed': 0,
					'failed': 0,
					'percentage': 0
				},
				':status': 'processing'
			}
		)

		# Dispatch job.started webhook event
		try:
			WebhookDispatcher.dispatch_job_started(
				job_id=job_id,
				user_id=job_data.get('user_id'),
				job_data=job_data
			)
		except Exception as webhook_error:
			logger.warning("Failed to dispatch job.started webhook", error=str(webhook_error))

	except Exception as e:
		print(f"Error updating progress: {str(e)}")

	# Initialize session with random user agent, referrer, proxy, and cookie handling
	proxy_config = job_data.get('proxy_config')
	render_config = job_data.get('render_config')
	session, session_data = initialize_session(job_id, proxy_config=proxy_config)

	try:
		# Process each URL
		for idx, url_item in enumerate(urls):
			url_start_time = time.time()
			url = url_item['url']

			try:
				# Check for timeout
				elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
				if elapsed > timeout_seconds:
					logger.warning("Job timeout reached", job_id=job_id, elapsed_seconds=elapsed)
					update_job_status(job_id, 'timeout')
					return {'status': 'timeout', 'message': f"Job timed out after {elapsed} seconds"}

				# Check if job was cancelled during processing
				job = get_job(job_id)
				if job and job.get('status') == 'cancelled':
					logger.info("Job cancellation detected", job_id=job_id)
					return {'status': 'cancelled', 'message': 'Job was cancelled during processing'}

				# Fetch URL (with proxy if configured)
				response = fetch_url_with_session(url, session, job_id, proxy_config=proxy_config, render_config=render_config)

				if response['status'] == 'success':
					# Process the page content
					page_content = response['content']
					url_results = process_queries(page_content, queries)

					# Store the results for this URL
					results[url] = {
						'status': 'success',
						'data': url_results
					}
					update_url_status(job_id, url, 'finished')
					processed_urls += 1

					# Log successful crawl
					url_duration_ms = (time.time() - url_start_time) * 1000
					logger.log_url_crawl(job_id, url, 'success', url_duration_ms,
									   queries_executed=len(queries))

					# Emit crawl success metric
					try:
						metrics.emit_crawl_success(job_id, url, url_duration_ms)
					except Exception:
						pass  # Ignore metrics errors

				else:
					# Handle failure
					results[url] = response
					update_url_status(job_id, url, 'error')
					failed_urls += 1

					# Log failed crawl
					url_duration_ms = (time.time() - url_start_time) * 1000
					logger.log_url_crawl(job_id, url, 'error', url_duration_ms,
									   error_message=response.get('message', 'Unknown error'))

					# Emit crawl failure metric
					try:
						error_type = response.get('message', 'unknown').split(':')[0].lower()
						metrics.emit_crawl_failure(job_id, url, error_type)
					except Exception:
						pass  # Ignore metrics errors

			except Exception as e:
				# Log exception during URL processing
				url_duration_ms = (time.time() - url_start_time) * 1000
				log_exception(logger, f"Error processing URL {url}", e, job_id=job_id, url=url)

				results[url] = {
					'status': 'error',
					'message': str(e)
				}
				update_url_status(job_id, url, 'error')
				failed_urls += 1

				logger.log_url_crawl(job_id, url, 'error', url_duration_ms, error_message=str(e))

				# Emit crawl failure metric
				try:
					error_type = type(e).__name__.lower()
					metrics.emit_crawl_failure(job_id, url, error_type)
				except Exception:
					pass  # Ignore metrics errors

			# Update progress every 10 URLs or on last URL
			if (idx + 1) % 10 == 0 or (idx + 1) == total_urls:
				percentage = int(((processed_urls + failed_urls) / total_urls) * 100)
				try:
					job_table.update_item(
						Key={'job_id': job_id},
						UpdateExpression="SET progress = :progress",
						ExpressionAttributeValues={
							':progress': {
								'total': total_urls,
								'processed': processed_urls,
								'failed': failed_urls,
								'percentage': percentage
							}
						}
					)
				except Exception as e:
					print(f"Error updating progress: {str(e)}")

	except Exception as e:
		print(f"Error processing job {job_id}: {str(e)}")
		# Optionally update job status as failed
		update_job_status(job_id, 'error')

		# Dispatch job.failed webhook event
		try:
			WebhookDispatcher.dispatch_job_failed(
				job_id=job_id,
				user_id=job_data.get('user_id'),
				job_data=job_data,
				error=str(e)
			)
		except Exception as webhook_error:
			logger.warning("Failed to dispatch job.failed webhook", error=str(webhook_error))

		return {'status': 'error', 'message': f"Error processing job: {str(e)}"}

	# Save session data for future reuse (this can be stored in DynamoDB or another persistent store)
	save_session_data(job_id, session_data)

	try:
		# Save the consolidated results to S3 or DynamoDB
		results_file_key = save_results_to_s3(results, job_id)
	except Exception as e:
		print(f"Error saving results for job {job_id} to S3: {str(e)}")
		return {'status': 'error', 'message': f"Failed to save results: {str(e)}"}

	# Update the job's last_run timestamp and status in the job table at the end of the process
	try:
		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="SET #last_run = :last_run, #status = :status, #results_s3_key = :results_s3_key",
			ExpressionAttributeNames={
				'#last_run': 'last_run',
				'#status': 'status',
				'#results_s3_key': 'results_s3_key'
			},
			ExpressionAttributeValues={
				':last_run': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
				':status': 'ready',
				':results_s3_key': results_file_key
			}
		)

		# Dispatch job.completed webhook event
		try:
			results_summary = {
				'total_urls': total_urls,
				'processed': processed_urls,
				'failed': failed_urls,
				'success_rate': (processed_urls / total_urls * 100) if total_urls > 0 else 0
			}
			WebhookDispatcher.dispatch_job_completed(
				job_id=job_id,
				user_id=job_data.get('user_id'),
				job_data=job_data,
				results_summary=results_summary
			)
		except Exception as webhook_error:
			logger.warning("Failed to dispatch job.completed webhook", error=str(webhook_error))

	except Exception as e:
		print(f"Error updating job status for job {job_id}: {str(e)}")
		return {'status': 'error', 'message': f"Failed to update job status: {str(e)}"}

	# Emit crawl success rate metric
	try:
		if total_urls > 0:
			metrics.emit_crawl_success_rate(job_id, processed_urls, total_urls)
	except Exception:
		pass  # Ignore metrics errors

	return results


# Refresh a job (re-crawl all URLs)
def refresh_job(job_id):
	"""
	Logic to manually trigger a re-crawl for a specific job.
	This function will update the job status and initiate a new crawl process.
	"""
	# Example logic to update job status and re-run the crawl
	response = job_table.get_item(Key={'job_id': job_id})

	if 'Item' in response:
		job_data = response['Item']

		# Re-parse the list of URLs from the external source
		new_links = parse_links_from_file(job_data['file_mapping'], job_data['source'])
  
		# Compare the new list with the old list to determine changes
		old_links = set(job_data['links'])
		added_links = set(new_links) - old_links
		removed_links = old_links - set(new_links)

		# Update the job data with the new list of links
		job_data['links'] = new_links
		job_table.put_item(Item=job_data)

		# Update the job status to 'queued'
		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="SET #status = :status, #last_updated = :last_updated",
			ExpressionAttributeNames={
				'#status': 'status',
				'#last_updated': 'last_updated'
			},
			ExpressionAttributeValues={
				':status': 'queued',
				':last_updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
			}
		)

		# Send URLs to the SQS queue for processing
		sqs = boto3.client('sqs')
		queue_url = os.environ['SQS_JOB_QUEUE_URL']

		for url in new_links:
			url_data = {
				'job_id': job_id,
				'url': url,
				'queries': job_data['queries'],
			}
			print(f"Sending URL {url} to SQS for job {job_id}")
			sqs.send_message(
				QueueUrl=queue_url,
				MessageBody=json.dumps(url_data)
			)

		# Update the last_run timestamp
		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="SET #last_run = :last_run",
			ExpressionAttributeNames={'#last_run': 'last_run'},
			ExpressionAttributeValues={
				':last_run': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
			}
		)

		return f"Job {job_id} refreshed and URLs sent to SQS successfully."

	else:
			return f"Job {job_id} not found."

# Resume a job (update status to "active")
def resume_job(job_id):
	try:
		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="set #st = :s",
			ExpressionAttributeNames={'#st': 'status'},
			ExpressionAttributeValues={':s': 'active'}
		)
		return f"Job {job_id} resumed successfully."
	except ClientError as e:
		print(f"Error resuming job: {e.response['Error']['Message']}")
		return None

# Update job information in DynamoDB
def update_job(job_id, job_data):
	try:
    # Validate the updated job data before updating
		validate_job_data(job_data)
  
		update_expression = "set "
		expression_attr_values = {}
		expression_attr_names = {}

		for key, value in job_data.items():
			update_expression += f"#{key} = :{key}, "
			expression_attr_values[f":{key}"] = value
			expression_attr_names[f"#{key}"] = key

		# Remove trailing comma and space
		update_expression = update_expression.rstrip(", ")

		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression=update_expression,
			ExpressionAttributeNames=expression_attr_names,
			ExpressionAttributeValues=expression_attr_values
		)
		return f"Job {job_id} updated successfully."
	except ValueError as e:
		print(f"Job validation failed: {str(e)}")
		return None
	except ClientError as e:
		print(f"Error updating job: {e.response['Error']['Message']}")
		return None

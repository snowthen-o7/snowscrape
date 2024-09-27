import boto3
import json
import os
import requests

from botocore.exceptions import ClientError
from crawl_manager import process_queries
from datetime import datetime, timezone
from typing import Any, Dict
from utils import decimal_to_float, delete_job_links, fetch_url_with_session, fetch_urls_for_job, initialize_session, parse_links_from_file, save_results_to_s3, save_session_data, update_job_status, update_url_status, validate_job_data

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'us-east-2'))
job_table = dynamodb.Table(os.environ['DYNAMODB_JOBS_TABLE'])
url_table = dynamodb.Table(os.environ['DYNAMODB_URLS_TABLE'])

# Create a new job in DynamoDB
def create_job(job_data):
	try:
		# Parse the list of URLs from the external source
		links = parse_links_from_file(job_data['file_mapping'], job_data['source'])  # Assuming 'source' is the URL to the list
		print(f"Parsed links: {links}")

		# Assign a job_id if it doesn't exist
		job_id = job_data.get('job_id')
		if not job_id:
			import uuid
			job_data['job_id'] = str(uuid.uuid4())

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
		}

		print(f"Creating job: {job_item}")
		# Insert job data into DynamoDB
		response = job_table.put_item(Item=job_item)
		print(f"DynamoDB put_item response: {response}")
  
  	# Insert URLs into the URL tracking table with state 'ready'
		for url in links:
			url_item = {
				'job_id': job_data['job_id'],
				'url': url,
				'state': 'ready',
				'last_updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
			}
			url_table.put_item(Item=url_item)
  
		return job_data['job_id']
	except ValueError as e:
		print(f"Job validation failed: {str(e)}")
		return None
	except ClientError as e:
		print(f"Error creating job: {e.response['Error']['Message']}")
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
def get_all_jobs():
	try:
		response = job_table.scan()
		print(f"Retrieved jobs response: {response}")
		jobs = response.get('Items', [])
		print(f"Jobs: {jobs}")
		jobs_cleaned = decimal_to_float(jobs)  # Convert Decimals
		return jobs_cleaned
	except ClientError as e:
		print(f"Error retrieving jobs: {e.response['Error']['Message']}")
		return []

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

	# Initialize session with random user agent, referrer, and cookie handling
	session, session_data = initialize_session(job_id)

	try:
		# Process each URL
		for url_item in urls:
			url = url_item['url']
			response = fetch_url_with_session(url, session, job_id)

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

			else:
				# Handle failure
				results[url] = response
				update_url_status(job_id, url, 'error')

	except Exception as e:
		print(f"Error processing job {job_id}: {str(e)}")
		# Optionally update job status as failed
		update_job_status(job_id, 'error')
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
	except Exception as e:
		print(f"Error updating job status for job {job_id}: {str(e)}")
		return {'status': 'error', 'message': f"Failed to update job status: {str(e)}"}

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

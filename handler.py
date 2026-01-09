import boto3
import json
import os
import paramiko
import time
import uuid

from connection_pool import get_table, get_s3_client, get_sqs_client
from crawl_manager import get_crawl
from datetime import datetime, timedelta, timezone
from job_manager import cancel_job, create_job, delete_job, get_all_jobs, get_job, get_job_crawls, pause_job, process_job, refresh_job, resume_job, update_job
from logger import get_logger, log_lambda_invocation, log_exception
from metrics import get_metrics_emitter
from observatory_client import get_observatory_client
from urllib.parse import urlparse
from utils import decimal_to_float, detect_csv_settings, extract_token_from_event, parse_links_from_file, refresh_job_urls, validate_clerk_token, validate_job_data

# Initialize logger, metrics, and observatory
logger = get_logger(__name__)
metrics = get_metrics_emitter()
observatory = get_observatory_client()

# Use connection pool for AWS services
job_table = get_table(os.environ['DYNAMODB_JOBS_TABLE'])
template_table = get_table(os.environ['DYNAMODB_TEMPLATES_TABLE'])
s3 = get_s3_client()
sqs = get_sqs_client()

# Health check endpoint
def health_check_handler(event, context):
	"""
	Health check endpoint for monitoring service availability.
	Tests connectivity to DynamoDB, S3, and SQS.
	Also reports health status to Observatory for centralized monitoring.
	"""
	start_time = time.time()
	health_status = {
		'status': 'healthy',
		'timestamp': datetime.now(timezone.utc).isoformat(),
		'service': 'snowscrape-backend',
		'version': '1.0.0',
		'checks': {}
	}

	try:
		# Check DynamoDB connectivity
		try:
			job_table.table_status
			health_status['checks']['dynamodb'] = {'status': 'healthy'}
		except Exception as e:
			health_status['checks']['dynamodb'] = {'status': 'unhealthy', 'error': str(e)}
			health_status['status'] = 'degraded'

		# Check S3 connectivity
		try:
			s3.list_buckets()
			health_status['checks']['s3'] = {'status': 'healthy'}
		except Exception as e:
			health_status['checks']['s3'] = {'status': 'unhealthy', 'error': str(e)}
			health_status['status'] = 'degraded'

		# Check SQS connectivity
		try:
			sqs.get_queue_url(QueueName=os.environ['SQS_JOB_QUEUE'])
			health_status['checks']['sqs'] = {'status': 'healthy'}
		except Exception as e:
			health_status['checks']['sqs'] = {'status': 'unhealthy', 'error': str(e)}
			health_status['status'] = 'degraded'

		# Calculate response time
		response_time_ms = int((time.time() - start_time) * 1000)

		# Report to Observatory (non-blocking - don't fail health check if Observatory is down)
		try:
			if health_status['status'] == 'healthy':
				observatory.report_health('healthy', response_time_ms)
			elif health_status['status'] == 'degraded':
				unhealthy_services = [
					service for service, check in health_status['checks'].items()
					if check['status'] == 'unhealthy'
				]
				error_msg = f"Degraded services: {', '.join(unhealthy_services)}"
				observatory.report_health('degraded', response_time_ms, error_msg)
			else:
				observatory.report_health('down', response_time_ms, 'Service down')
		except Exception as obs_error:
			# Don't fail health check if Observatory reporting fails
			logger.warning("Failed to report health to Observatory", error=str(obs_error))

		# Determine overall status code
		status_code = 200 if health_status['status'] == 'healthy' else 503

		logger.info("Health check completed", overall_status=health_status['status'],
				   response_time_ms=response_time_ms)

		return {
			'statusCode': status_code,
			'body': json.dumps(health_status),
			'headers': {
				'Access-Control-Allow-Origin': '*',
				'Content-Type': 'application/json',
				'Cache-Control': 'no-cache, no-store, must-revalidate'
			}
		}

	except Exception as e:
		log_exception(logger, "Health check failed", e)

		# Report critical failure to Observatory
		try:
			response_time_ms = int((time.time() - start_time) * 1000)
			observatory.report_health('down', response_time_ms, str(e))
		except Exception:
			pass  # Don't fail if Observatory is unreachable

		return {
			'statusCode': 503,
			'body': json.dumps({
				'status': 'unhealthy',
				'timestamp': datetime.now(timezone.utc).isoformat(),
				'error': str(e)
			}),
			'headers': {
				'Access-Control-Allow-Origin': '*',
				'Content-Type': 'application/json'
			}
		}

# Create a new job
def create_job_handler(event, context):
	start_time = time.time()
	log_lambda_invocation(event, context, logger)

	try:
		# Authentication
		token = extract_token_from_event(event)
		if not token:
			logger.warning("Authentication failed - No token provided")
			duration_ms = (time.time() - start_time) * 1000
			logger.log_request('POST', '/jobs', 401, duration_ms)
			return {
				"statusCode": 401,
				"body": json.dumps({"message": "Unauthorized - No token provided"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		try:
			user_data = validate_clerk_token(token)
			logger.info("User authenticated", user_id=user_data.get("sub"))
		except Exception as e:
			logger.warning("Token validation failed", error=str(e))
			duration_ms = (time.time() - start_time) * 1000
			logger.log_request('POST', '/jobs', 401, duration_ms)
			return {
				"statusCode": 401,
				"body": json.dumps({"message": str(e)}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Parse and validate job data
		job_data = json.loads(event['body'])
		validate_job_data(job_data)
		job_data["user_id"] = user_data["sub"]

		logger.info("Creating job", job_name=job_data.get('name'), user_id=user_data.get("sub"))

		# Create job
		job_id = create_job(job_data)

		if job_id:
			logger.log_job_event(job_id, 'created', 'ready', job_name=job_data.get('name'))

			# Emit custom metrics for job creation
			try:
				url_count = len(job_data.get('links', []))
				metrics.emit_job_created(job_id, url_count)
			except Exception as metrics_error:
				logger.warning("Failed to emit job creation metrics", error=str(metrics_error))

			duration_ms = (time.time() - start_time) * 1000
			logger.log_request('POST', '/jobs', 201, duration_ms, job_id=job_id)

			return {
				"statusCode": 201,
				"body": json.dumps({"message": "Job created successfully", "job_id": job_id}),
				"headers": {
					'Access-Control-Allow-Credentials': True,
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}
		else:
			logger.error("Job creation failed", job_data=job_data)
			duration_ms = (time.time() - start_time) * 1000
			logger.log_request('POST', '/jobs', 500, duration_ms)

			return {
				"statusCode": 500,
				"body": json.dumps({"message": "Failed to create job"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

	except ValueError as e:
		log_exception(logger, "Job validation failed", e)
		duration_ms = (time.time() - start_time) * 1000
		logger.log_request('POST', '/jobs', 400, duration_ms)

		return {
			"statusCode": 400,
			"body": json.dumps({"message": f"Validation error: {str(e)}"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	except Exception as e:
		log_exception(logger, "Unexpected error in create_job_handler", e)
		duration_ms = (time.time() - start_time) * 1000
		logger.log_request('POST', '/jobs', 500, duration_ms)

		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Internal server error"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
	finally:
		logger.clear_context()

# Delete a job and cancel all associated crawls
def delete_job_handler(event, context):
	print(event)

	# Authentication
	token = extract_token_from_event(event)
	if not token:
		return {
			"statusCode": 401,
			"body": json.dumps({"message": "Unauthorized - No token provided"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	user_id = validate_clerk_token(token)
	if not user_id:
		return {
			"statusCode": 401,
			"body": json.dumps({"message": "Unauthorized - Invalid token"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	job_id = event['pathParameters']['job_id']
	delete_job(job_id)
	return {
		"statusCode": 200,
		"body": json.dumps({"message": "Job deleted successfully", "job_id": job_id}),
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}

# Get the status of all jobs
def get_all_job_statuses_handler(event, context):
	"""
	Get all job statuses with pagination support.

	Query parameters:
		- limit: Number of items to return (default: 50, max: 100)
		- last_key: Base64-encoded pagination key
	"""
	try:
		# Extract pagination parameters from query string
		query_params = event.get('queryStringParameters') or {}
		limit = min(int(query_params.get('limit', 50)), 100)  # Max 100 items per request

		last_evaluated_key = None
		if 'last_key' in query_params:
			# Decode pagination key (base64 encoded JSON)
			import base64
			try:
				last_evaluated_key = json.loads(base64.b64decode(query_params['last_key']))
			except Exception as e:
				logger.warning("Invalid pagination key", error=str(e))

		# Fetch jobs with pagination
		result = get_all_jobs(limit=limit, last_evaluated_key=last_evaluated_key)

		# Encode pagination key for response
		response_body = {
			'jobs': result['items'],
			'count': len(result['items'])
		}

		if 'last_evaluated_key' in result:
			response_body['last_key'] = base64.b64encode(
				json.dumps(result['last_evaluated_key']).encode()
			).decode()

		logger.info("Retrieved job statuses", count=len(result['items']))

		return {
			"statusCode": 200,
			"body": json.dumps(response_body),
			"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
	except Exception as e:
		log_exception(logger, "Error retrieving job statuses", e)
		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Internal server error"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

# Get specific crawl details
def get_crawl_handler(event, context):
	print(event)
	job_id = event['pathParameters']['job_id']
	crawl_id = event['pathParameters']['crawl_id']
	crawl = get_crawl(job_id, crawl_id)
	if crawl:
		return {
			"statusCode": 200,
			"body": json.dumps(crawl),
			"headers": {
					'Access-Control-Allow-Credentials': True,
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
		}
	else:
		return {
			"statusCode": 404,
			"body": json.dumps({"message": "Crawl not found"}),
			"headers": {
					'Access-Control-Allow-Credentials': True,
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
		}

# Get all crawls for a job
def get_job_crawls_handler(event, context):
	print(event)
	job_id = event['pathParameters']['job_id']
	crawls = get_job_crawls(job_id)
	return {
		"statusCode": 200,
		"body": json.dumps(crawls),
			"headers": {
					'Access-Control-Allow-Credentials': True,
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
	}

# Get job details
def get_job_details_handler(event, context):
	print(event)
	job_id = event['pathParameters']['job_id']
	job = get_job(job_id)
	if job:
		return {
			"statusCode": 200,
			"body": json.dumps(job),
			"headers": {
					'Access-Control-Allow-Credentials': True,
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
		}
	else:
		return {
			"statusCode": 404,
			"body": json.dumps({"message": "Job not found"}),
			"headers": {
					'Access-Control-Allow-Credentials': True,
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
		}

# Pause a job
def pause_job_handler(event, context):
	print(event)

	# Authentication
	token = extract_token_from_event(event)
	if not token:
		return {
			"statusCode": 401,
			"body": json.dumps({"message": "Unauthorized - No token provided"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	user_id = validate_clerk_token(token)
	if not user_id:
		return {
			"statusCode": 401,
			"body": json.dumps({"message": "Unauthorized - Invalid token"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	job_id = event['pathParameters']['job_id']
	pause_job(job_id)
	return {
		"statusCode": 200,
		"body": json.dumps({"message": "Job paused successfully", "job_id": job_id}),
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}

# Cancel a job
def cancel_job_handler(event, context):
	print(event)

	# Authentication
	token = extract_token_from_event(event)
	if not token:
		return {
			"statusCode": 401,
			"body": json.dumps({"message": "Unauthorized - No token provided"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	user_id = validate_clerk_token(token)
	if not user_id:
		return {
			"statusCode": 401,
			"body": json.dumps({"message": "Unauthorized - Invalid token"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	job_id = event['pathParameters']['job_id']
	result = cancel_job(job_id)

	if result:
		return {
			"statusCode": 200,
			"body": json.dumps({"message": "Job cancelled successfully", "job_id": job_id}),
			"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
	else:
		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Failed to cancel job", "job_id": job_id}),
			"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

# Process a job (Triggered by SQS)
def process_job_handler(event, context):
	start_time = time.time()
	log_lambda_invocation(event, context, logger)

	processed_count = 0
	failed_count = 0

	try:
		# Process each message from SQS
		for record in event['Records']:
			record_start_time = time.time()
			job_id = None

			try:
				# Parse job data
				job_data = json.loads(record['body'])
				job_id = job_data.get('job_id')

				logger.set_context(job_id=job_id, message_id=record.get('messageId'))
				logger.log_job_event(job_id, 'processing_started', 'processing',
									message_id=record.get('messageId'))

				# Perform job processing
				result = process_job(job_data)

				# Check if job was cancelled or timed out
				if isinstance(result, dict):
					result_status = result.get('status')
					record_duration_ms = (time.time() - record_start_time) * 1000

					if result_status == 'cancelled':
						logger.log_job_event(job_id, 'cancelled', 'cancelled')
						metrics.emit_job_processing_duration(job_id, record_duration_ms, 'cancelled')
						processed_count += 1
						continue
					elif result_status == 'timeout':
						logger.log_job_event(job_id, 'timeout', 'timeout')
						metrics.emit_job_processing_duration(job_id, record_duration_ms, 'timeout')
						failed_count += 1
						continue
					elif result_status == 'error':
						logger.error("Job processing failed", job_id=job_id,
									error_message=result.get('message'))
						metrics.emit_job_processing_duration(job_id, record_duration_ms, 'error')
						failed_count += 1
						continue

				# Store the result in S3
				try:
					s3_upload_start = time.time()
					result_json = json.dumps(result)
					s3.put_object(
						Bucket=os.environ['S3_BUCKET'],
						Key=f'jobs/{job_id}/result.json',
						Body=result_json
					)
					s3_upload_duration = (time.time() - s3_upload_start) * 1000
					logger.info("Results saved to S3", job_id=job_id,
							   s3_key=f'jobs/{job_id}/result.json')

					# Emit S3 upload metrics
					try:
						metrics.emit_s3_upload(job_id, len(result_json.encode('utf-8')), s3_upload_duration)
					except Exception:
						pass  # Ignore metrics errors
				except Exception as s3_error:
					log_exception(logger, "Failed to save results to S3", s3_error, job_id=job_id)
					# Continue - don't fail the entire job if S3 save fails

				# Update DynamoDB with job status
				try:
					job_table.update_item(
						Key={'job_id': job_id},
						UpdateExpression="SET #status = :status, #last_updated = :last_updated",
						ExpressionAttributeNames={'#status': 'status', '#last_updated': 'last_updated'},
						ExpressionAttributeValues={
							':status': 'ready',
							':last_updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
						}
					)

					record_duration_ms = (time.time() - record_start_time) * 1000
					logger.log_job_event(job_id, 'completed', 'ready',
									   duration_ms=record_duration_ms)

					# Emit job completion metrics
					try:
						metrics.emit_job_processing_duration(job_id, record_duration_ms, 'completed')
						# Emit URLs processed count if available in result
						if isinstance(result, dict):
							urls_processed = len(result.get('crawl_results', []))
							if urls_processed > 0:
								metrics.emit_urls_processed(job_id, urls_processed)
					except Exception:
						pass  # Ignore metrics errors

					processed_count += 1

				except Exception as db_error:
					log_exception(logger, "Failed to update job status", db_error, job_id=job_id)
					failed_count += 1

			except json.JSONDecodeError as e:
				log_exception(logger, "Invalid JSON in SQS message", e,
							message_id=record.get('messageId'))
				failed_count += 1

			except Exception as e:
				log_exception(logger, "Error processing job record", e,
							job_id=job_id, message_id=record.get('messageId'))
				failed_count += 1

			finally:
				logger.clear_context()

		# Log batch processing summary
		total_duration_ms = (time.time() - start_time) * 1000
		logger.info("Batch processing completed",
				   total_records=len(event['Records']),
				   processed=processed_count,
				   failed=failed_count,
				   duration_ms=total_duration_ms)

		return {
			'statusCode': 200,
			'body': json.dumps({
				"message": "Job batch processed",
				"processed": processed_count,
				"failed": failed_count
			}),
			"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	except Exception as e:
		log_exception(logger, "Fatal error in process_job_handler", e)
		return {
			'statusCode': 500,
			'body': json.dumps({"message": "Internal server error"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

# Refresh a job (manual re-crawl)
def refresh_job_handler(event, context):
	print(event)
	job_id = event['pathParameters']['job_id']
	refresh_job(job_id)
	return {
		"statusCode": 200,
		"body": json.dumps({"message": "Job refreshed successfully", "job_id": job_id}),
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}

# Resume a job
def resume_job_handler(event, context):
	print(event)
	job_id = event['pathParameters']['job_id']
	resume_job(job_id)
	return {
		"statusCode": 200,
		"body": json.dumps({"message": "Job resumed successfully", "job_id": job_id}),
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}

def schedule_jobs_handler(event, context):
	"""
	This function runs on a schedule (e.g., every hour) and finds jobs that need to be run,
	sending them to SQS for processing.
	"""
	# Get current time to check jobs that need to be run
	current_time = datetime.now(timezone.utc)
	current_day = current_time.strftime('%A')  # E.g., 'Monday', 'Tuesday'
	current_hour = current_time.hour  # E.g., 14 for 2 PM
	current_minute = current_time.minute  # E.g., 45 for 45 minutes past the hour
	print(f"Current time: {current_time}, Day: {current_day}, Hour: {current_hour}, Minute: {current_minute}")
	
	# Scan for jobs that are ready to run and have scheduling criteria
	jobs = job_table.scan(
		FilterExpression="attribute_exists(scheduling) AND #status = :ready",
		ExpressionAttributeNames={"#status": "status"},
		ExpressionAttributeValues={":ready": "ready"}
	).get('Items', [])
	
	jobs_cleaned = decimal_to_float(jobs)
 
	print(f"Jobs to process: {jobs_cleaned}")
	for job in jobs_cleaned:
		scheduling = job.get('scheduling', {})
		job_days = scheduling.get('days', [])  # E.g., ['Monday', 'Wednesday']
		job_hours = scheduling.get('hours', [])  # E.g., [12, 14] for 12 PM and 2 PM or 24 for "Every Hour"
		job_minutes = scheduling.get('minutes', [])  # E.g., [0, 15, 30, 45] for multiples of 5

		# Check if the job has a last_run timestamp
		last_run_str = job.get('last_run')
		last_run = datetime.strptime(last_run_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) if last_run_str else None

		# If 'Every Day' is in the job_days, it means the job should run every day
		should_run_today = 'Every Day' in job_days or current_day in job_days
		
		# If '24' is in the job_hours, it means the job should run every hour
		should_run_this_hour = 24 in job_hours or current_hour in job_hours
  
		# Determine if the job should run this minute (based on multiples of 5)
		should_run_this_minute = 60 in job_minutes or current_minute in job_minutes
		
		print(f"Job {job['job_id']} - Days: {job_days}, Hours: {job_hours}, Minutes: {job_minutes}, Last Run: {last_run}, Should Run Today: {should_run_today}, Should Run This Hour: {should_run_this_hour}, Should Run This Minute: {should_run_this_minute}")

		# Check if the job should run based on its scheduling
		if should_run_today and should_run_this_hour and should_run_this_minute:
			# If last_run exists, check if the current time is after the next scheduled run
			if last_run:
				# Calculate the next scheduled minute for the job
				next_scheduled_minute = min([minute for minute in job_minutes if minute > last_run.minute], default=job_minutes[0])

				# If the next minute has already passed for the current hour, move to the next hour
				if next_scheduled_minute <= last_run.minute:
					next_run_time = last_run.replace(hour=(last_run.hour + 1) % 24, minute=int(next_scheduled_minute), second=0, microsecond=0)
				else:
					next_run_time = last_run.replace(minute=int(next_scheduled_minute), second=0, microsecond=0)

				# Compare current time to the next calculated run time
				if current_time < next_run_time:
					print(f"Job {job['job_id']} was already run recently, skipping.")
					continue

			# Refresh the URLs by re-pulling from the source file
			try:
				links = parse_links_from_file(job['file_mapping'], job['source'])
				print(f"Refreshed links for job {job['job_id']}: {links}")

				# Update the URL table with the refreshed links
				refresh_job_urls(job['job_id'], links)

			except Exception as e:
				print(f"Failed to refresh URLs for job {job['job_id']}: {e}")
				continue

			# Send the job to the SQS queue for processing
			print(f"Scheduling job {job['job_id']} for processing.")
			sqs.send_message(
				QueueUrl=os.environ['SQS_JOB_QUEUE_URL'],
				MessageBody=json.dumps(job)
			)

			# Update the job status to queued
			job_table.update_item(
				Key={'job_id': job['job_id']},
				UpdateExpression="SET #status = :queued, #last_run = :last_run, #last_updated = :last_updated",
				ExpressionAttributeNames={
					'#status': 'status',
					'#last_run': 'last_run',
					'#last_updated': 'last_updated'
				},
				ExpressionAttributeValues={
					':queued': 'queued',
					':last_run': current_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
					':last_updated': current_time.strftime('%Y-%m-%dT%H:%M:%SZ')
				}
			)
		else:
			print(f"Job {job['job_id']} is not scheduled to run at this time.")


# Report aggregated metrics to Observatory (scheduled hourly)
def report_metrics_to_observatory_handler(event, context):
	"""
	Scheduled function that aggregates metrics and sends them to Observatory.
	Runs hourly to provide business KPI visibility across the ecosystem.
	"""
	try:
		logger.info("Starting metrics aggregation for Observatory")

		# Define time period (last hour)
		end_time = datetime.now(timezone.utc)
		start_time = end_time - timedelta(hours=1)
		start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')

		# Get URL table for crawl metrics
		url_table = get_table(os.environ['DYNAMODB_URLS_TABLE'])

		# Query jobs from last hour
		jobs_response = job_table.scan(
			FilterExpression="last_updated >= :start_time",
			ExpressionAttributeValues={':start_time': start_time_str}
		)
		jobs = decimal_to_float(jobs_response.get('Items', []))

		# Calculate job metrics
		jobs_completed = len([j for j in jobs if j.get('status') == 'ready' and j.get('last_run')])
		jobs_failed = len([j for j in jobs if j.get('status') == 'error'])
		jobs_cancelled = len([j for j in jobs if j.get('status') == 'cancelled'])
		jobs_timeout = len([j for j in jobs if j.get('status') == 'timeout'])
		total_jobs = jobs_completed + jobs_failed + jobs_cancelled + jobs_timeout

		# Calculate success rate
		if total_jobs > 0:
			success_rate = (jobs_completed / total_jobs) * 100
			error_rate = ((jobs_failed + jobs_timeout) / total_jobs) * 100
		else:
			success_rate = 100.0
			error_rate = 0.0

		# Get active jobs count
		active_jobs_response = job_table.scan(
			FilterExpression="#status = :processing",
			ExpressionAttributeNames={'#status': 'status'},
			ExpressionAttributeValues={':processing': 'processing'}
		)
		active_jobs = len(active_jobs_response.get('Items', []))

		# Get queue depth from SQS
		try:
			queue_attrs = sqs.get_queue_attributes(
				QueueUrl=os.environ['SQS_JOB_QUEUE_URL'],
				AttributeNames=['ApproximateNumberOfMessages']
			)
			queue_depth = int(queue_attrs['Attributes']['ApproximateNumberOfMessages'])
		except Exception as e:
			logger.warning("Failed to get queue depth", error=str(e))
			queue_depth = 0

		# Query URL crawl metrics from last hour
		urls_response = url_table.scan(
			FilterExpression="last_updated >= :start_time",
			ExpressionAttributeValues={':start_time': start_time_str}
		)
		urls = decimal_to_float(urls_response.get('Items', []))

		urls_crawled = len(urls)
		urls_successful = len([u for u in urls if u.get('state') == 'finished'])
		urls_failed = len([u for u in urls if u.get('state') == 'error'])

		# Calculate average crawl duration (if we have duration data)
		# Note: This would require storing duration in URL records
		# For now, we'll use a placeholder or skip it
		avg_crawl_duration_ms = 0  # Placeholder

		# Send batch metrics to Observatory
		logger.info("Sending metrics to Observatory",
				   jobs_processed=total_jobs,
				   success_rate=success_rate,
				   urls_crawled=urls_crawled)

		observatory.send_batch_metrics(
			jobs_processed=total_jobs,
			jobs_completed=jobs_completed,
			jobs_failed=jobs_failed + jobs_timeout,
			success_rate=success_rate,
			avg_crawl_duration_ms=avg_crawl_duration_ms,
			active_jobs=active_jobs,
			queue_depth=queue_depth,
			urls_crawled=urls_crawled,
			error_rate=error_rate
		)

		# Track metrics reporting event
		observatory.track_event('metrics_reported', {
			'period_start': start_time.isoformat(),
			'period_end': end_time.isoformat(),
			'jobs_processed': total_jobs,
			'urls_crawled': urls_crawled
		})

		logger.info("Metrics successfully reported to Observatory")

		return {
			'statusCode': 200,
			'body': json.dumps({
				'message': 'Metrics reported successfully',
				'metrics': {
					'jobs_processed': total_jobs,
					'success_rate': round(success_rate, 2),
					'active_jobs': active_jobs,
					'queue_depth': queue_depth,
					'urls_crawled': urls_crawled
				}
			})
		}

	except Exception as e:
		log_exception(logger, "Failed to report metrics to Observatory", e)
		return {
			'statusCode': 500,
			'body': json.dumps({
				'message': 'Failed to report metrics',
				'error': str(e)
			})
		}


# Update a job
def update_job_handler(event, context):
	print(event)

	# Authentication
	token = extract_token_from_event(event)
	if not token:
		return {
			"statusCode": 401,
			"body": json.dumps({"message": "Unauthorized - No token provided"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	user_id = validate_clerk_token(token)
	if not user_id:
		return {
			"statusCode": 401,
			"body": json.dumps({"message": "Unauthorized - Invalid token"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	job_id = event['pathParameters']['job_id']
	job_data = json.loads(event['body'])
	validate_job_data(job_data)
	update_job(job_id, job_data)
	return {
		"statusCode": 200,
		"body": json.dumps({"message": "Job updated successfully", "job_id": job_id}),
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}

def validate_sftp_url_handler(event, context):
	# Extract URL from the request body
	body = json.loads(event.get('body', '{}'))
	sftp_url = body.get('sftp_url')

	if not sftp_url:
		return {
			'statusCode': 400,
			'body': json.dumps({'error': 'Missing SFTP URL'}),
			"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	# Parse the SFTP URL
	parsed_url = urlparse(sftp_url)

	if parsed_url.scheme != 'sftp':
		return {
			'statusCode': 400,
			'body': json.dumps({'error': 'Invalid URL scheme'}),
			"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
  
  # Extract username and password from the URL
	username = parsed_url.username
	password = parsed_url.password

	if not username or not password:
		return {
			'statusCode': 400,
			'body': json.dumps({'error': 'Missing username or password in the URL'}),
			"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	# Attempt to connect to the SFTP server
	try:
		transport = paramiko.Transport((parsed_url.hostname, parsed_url.port or 22))
		transport.connect(username=username, password=password)
		sftp = paramiko.SFTPClient.from_transport(transport)

		# Retrieve the file content
		with sftp.file(parsed_url.path, 'r') as file:
			file_content = file.read().decode()  # Decode file content to string

		sftp.close()
		transport.close()
  
		# Detect CSV settings from the file content
		csv_settings = detect_csv_settings(file_content)

		return {
			'statusCode': 200,
			'body': json.dumps({
					'message': 'SFTP URL validated successfully',
					'delimiter': csv_settings['delimiter'],
					'enclosure': csv_settings['enclosure'],
					'escape': csv_settings['escape'],
					'headers': csv_settings['headers']
			}),
			"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	except Exception as e:
		return {
			'statusCode': 400,
			'body': json.dumps({'error': str(e)}),
			"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}


# Download job results
def download_results_handler(event, context):
	"""
	Generate a pre-signed S3 URL for downloading job results.
	Supports both JSON and CSV formats.
	"""
	start_time = time.time()
	log_lambda_invocation(event, context, logger)

	try:
		# Authentication
		token = extract_token_from_event(event)
		if not token:
			logger.warning("Authentication failed - No token provided")
			return {
				"statusCode": 401,
				"body": json.dumps({"message": "Unauthorized - No token provided"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		try:
			user_data = validate_clerk_token(token)
			logger.info("User authenticated", user_id=user_data.get("sub"))
		except Exception as e:
			logger.warning("Token validation failed", error=str(e))
			return {
				"statusCode": 401,
				"body": json.dumps({"message": str(e)}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Get job ID from path
		job_id = event['pathParameters']['job_id']

		# Get format from query parameters (default to json)
		query_params = event.get('queryStringParameters') or {}
		file_format = query_params.get('format', 'json').lower()

		if file_format not in ['json', 'csv']:
			return {
				"statusCode": 400,
				"body": json.dumps({"message": "Invalid format. Use 'json' or 'csv'"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Construct S3 key
		s3_key = f'jobs/{job_id}/result.json'

		# Check if file exists
		try:
			s3.head_object(Bucket=os.environ['S3_BUCKET'], Key=s3_key)
		except Exception:
			logger.warning("Results file not found", job_id=job_id, s3_key=s3_key)
			return {
				"statusCode": 404,
				"body": json.dumps({"message": "Results not found for this job"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Generate pre-signed URL (valid for 1 hour)
		presigned_url = s3.generate_presigned_url(
			'get_object',
			Params={
				'Bucket': os.environ['S3_BUCKET'],
				'Key': s3_key,
				'ResponseContentDisposition': f'attachment; filename="job_{job_id}_results.{file_format}"'
			},
			ExpiresIn=3600  # 1 hour
		)

		duration_ms = (time.time() - start_time) * 1000
		logger.info("Download URL generated", job_id=job_id, format=file_format, duration_ms=duration_ms)

		return {
			"statusCode": 200,
			"body": json.dumps({
				"download_url": presigned_url,
				"expires_in": 3600,
				"format": file_format
			}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	except Exception as e:
		log_exception(logger, "Failed to generate download URL", e)
		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Failed to generate download URL", "error": str(e)}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
	finally:
		logger.clear_context()


# Preview job results with pagination
def preview_results_handler(event, context):
	"""
	Fetch paginated job results for preview.
	Returns a subset of results with metadata for pagination.
	"""
	start_time = time.time()
	log_lambda_invocation(event, context, logger)

	try:
		# Authentication
		token = extract_token_from_event(event)
		if not token:
			logger.warning("Authentication failed - No token provided")
			return {
				"statusCode": 401,
				"body": json.dumps({"message": "Unauthorized - No token provided"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		try:
			user_data = validate_clerk_token(token)
			logger.info("User authenticated", user_id=user_data.get("sub"))
		except Exception as e:
			logger.warning("Token validation failed", error=str(e))
			return {
				"statusCode": 401,
				"body": json.dumps({"message": str(e)}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Get job ID from path
		job_id = event['pathParameters']['job_id']

		# Get pagination parameters from query
		query_params = event.get('queryStringParameters') or {}
		page = int(query_params.get('page', 1))
		page_size = int(query_params.get('page_size', 50))

		# Validate pagination parameters
		if page < 1:
			page = 1
		if page_size < 1 or page_size > 100:
			page_size = 50

		# Construct S3 key
		s3_key = f'jobs/{job_id}/result.json'

		# Fetch results from S3
		try:
			response = s3.get_object(Bucket=os.environ['S3_BUCKET'], Key=s3_key)
			results_data = json.loads(response['Body'].read().decode('utf-8'))
		except Exception as e:
			logger.warning("Results file not found", job_id=job_id, s3_key=s3_key, error=str(e))
			return {
				"statusCode": 404,
				"body": json.dumps({"message": "Results not found for this job"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Extract results array
		results = results_data.get('results', [])
		total_count = len(results)

		# Calculate pagination
		start_index = (page - 1) * page_size
		end_index = start_index + page_size
		paginated_results = results[start_index:end_index]

		# Calculate total pages
		total_pages = (total_count + page_size - 1) // page_size

		# Get column names from first result
		columns = []
		if len(results) > 0:
			columns = list(results[0].keys())

		duration_ms = (time.time() - start_time) * 1000
		logger.info("Results preview fetched", job_id=job_id, page=page, page_size=page_size, total_count=total_count, duration_ms=duration_ms)

		return {
			"statusCode": 200,
			"body": json.dumps({
				"results": paginated_results,
				"pagination": {
					"page": page,
					"page_size": page_size,
					"total_count": total_count,
					"total_pages": total_pages,
					"has_next": page < total_pages,
					"has_previous": page > 1
				},
				"columns": columns
			}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	except Exception as e:
		log_exception(logger, "Failed to fetch results preview", e)
		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Failed to fetch results preview", "error": str(e)}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
	finally:
		logger.clear_context()


# Template CRUD operations
def create_template_handler(event, context):
	"""
	Create a new job template from job configuration.
	Allows users to save job configurations for reuse.
	"""
	start_time = time.time()
	log_lambda_invocation(event, context, logger)

	try:
		# Authentication
		token = extract_token_from_event(event)
		if not token:
			logger.warning("Authentication failed - No token provided")
			return {
				"statusCode": 401,
				"body": json.dumps({"message": "Unauthorized - No token provided"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		try:
			user_data = validate_clerk_token(token)
			user_id = user_data.get("sub")
			logger.info("User authenticated", user_id=user_id)
		except Exception as e:
			logger.warning("Token validation failed", error=str(e))
			return {
				"statusCode": 401,
				"body": json.dumps({"message": str(e)}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Parse request body
		body = json.loads(event['body'])

		# Validate required fields
		if not body.get('name'):
			return {
				"statusCode": 400,
				"body": json.dumps({"message": "Template name is required"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		if not body.get('config'):
			return {
				"statusCode": 400,
				"body": json.dumps({"message": "Template configuration is required"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Generate template ID
		template_id = str(uuid.uuid4())

		# Create template item
		template = {
			'template_id': template_id,
			'user_id': user_id,
			'name': body['name'],
			'description': body.get('description', ''),
			'config': body['config'],
			'created_at': datetime.now(timezone.utc).isoformat(),
			'last_used': None
		}

		# Save to DynamoDB
		template_table.put_item(Item=template)

		duration_ms = (time.time() - start_time) * 1000
		logger.info("Template created", template_id=template_id, user_id=user_id, duration_ms=duration_ms)

		return {
			"statusCode": 201,
			"body": json.dumps({
				"message": "Template created successfully",
				"template_id": template_id,
				"template": template
			}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	except Exception as e:
		log_exception(logger, "Failed to create template", e)
		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Failed to create template", "error": str(e)}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
	finally:
		logger.clear_context()


def list_templates_handler(event, context):
	"""
	List all templates for the authenticated user.
	"""
	start_time = time.time()
	log_lambda_invocation(event, context, logger)

	try:
		# Authentication
		token = extract_token_from_event(event)
		if not token:
			logger.warning("Authentication failed - No token provided")
			return {
				"statusCode": 401,
				"body": json.dumps({"message": "Unauthorized - No token provided"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		try:
			user_data = validate_clerk_token(token)
			user_id = user_data.get("sub")
			logger.info("User authenticated", user_id=user_id)
		except Exception as e:
			logger.warning("Token validation failed", error=str(e))
			return {
				"statusCode": 401,
				"body": json.dumps({"message": str(e)}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Query templates by user_id using GSI
		response = template_table.query(
			IndexName='UserIdIndex',
			KeyConditionExpression='user_id = :user_id',
			ExpressionAttributeValues={
				':user_id': user_id
			}
		)

		templates = response.get('Items', [])

		# Sort by created_at descending (newest first)
		templates.sort(key=lambda x: x.get('created_at', ''), reverse=True)

		duration_ms = (time.time() - start_time) * 1000
		logger.info("Templates listed", user_id=user_id, count=len(templates), duration_ms=duration_ms)

		return {
			"statusCode": 200,
			"body": json.dumps(templates),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	except Exception as e:
		log_exception(logger, "Failed to list templates", e)
		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Failed to list templates", "error": str(e)}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
	finally:
		logger.clear_context()


def get_template_handler(event, context):
	"""
	Get a specific template by ID.
	"""
	start_time = time.time()
	log_lambda_invocation(event, context, logger)

	try:
		# Authentication
		token = extract_token_from_event(event)
		if not token:
			logger.warning("Authentication failed - No token provided")
			return {
				"statusCode": 401,
				"body": json.dumps({"message": "Unauthorized - No token provided"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		try:
			user_data = validate_clerk_token(token)
			user_id = user_data.get("sub")
			logger.info("User authenticated", user_id=user_id)
		except Exception as e:
			logger.warning("Token validation failed", error=str(e))
			return {
				"statusCode": 401,
				"body": json.dumps({"message": str(e)}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Get template ID from path
		template_id = event['pathParameters']['template_id']

		# Fetch template from DynamoDB
		response = template_table.get_item(Key={'template_id': template_id})

		if 'Item' not in response:
			logger.warning("Template not found", template_id=template_id)
			return {
				"statusCode": 404,
				"body": json.dumps({"message": "Template not found"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		template = response['Item']

		# Verify user owns this template
		if template['user_id'] != user_id:
			logger.warning("Unauthorized access attempt", template_id=template_id, user_id=user_id)
			return {
				"statusCode": 403,
				"body": json.dumps({"message": "You don't have permission to access this template"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Update last_used timestamp
		template_table.update_item(
			Key={'template_id': template_id},
			UpdateExpression='SET last_used = :timestamp',
			ExpressionAttributeValues={
				':timestamp': datetime.now(timezone.utc).isoformat()
			}
		)

		duration_ms = (time.time() - start_time) * 1000
		logger.info("Template retrieved", template_id=template_id, user_id=user_id, duration_ms=duration_ms)

		return {
			"statusCode": 200,
			"body": json.dumps(template),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	except Exception as e:
		log_exception(logger, "Failed to get template", e)
		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Failed to get template", "error": str(e)}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
	finally:
		logger.clear_context()


def delete_template_handler(event, context):
	"""
	Delete a template by ID.
	"""
	start_time = time.time()
	log_lambda_invocation(event, context, logger)

	try:
		# Authentication
		token = extract_token_from_event(event)
		if not token:
			logger.warning("Authentication failed - No token provided")
			return {
				"statusCode": 401,
				"body": json.dumps({"message": "Unauthorized - No token provided"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		try:
			user_data = validate_clerk_token(token)
			user_id = user_data.get("sub")
			logger.info("User authenticated", user_id=user_id)
		except Exception as e:
			logger.warning("Token validation failed", error=str(e))
			return {
				"statusCode": 401,
				"body": json.dumps({"message": str(e)}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Get template ID from path
		template_id = event['pathParameters']['template_id']

		# Fetch template to verify ownership
		response = template_table.get_item(Key={'template_id': template_id})

		if 'Item' not in response:
			logger.warning("Template not found", template_id=template_id)
			return {
				"statusCode": 404,
				"body": json.dumps({"message": "Template not found"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		template = response['Item']

		# Verify user owns this template
		if template['user_id'] != user_id:
			logger.warning("Unauthorized deletion attempt", template_id=template_id, user_id=user_id)
			return {
				"statusCode": 403,
				"body": json.dumps({"message": "You don't have permission to delete this template"}),
				"headers": {
					'Access-Control-Allow-Origin': '*',
					"Content-Type": "application/json"
				}
			}

		# Delete template
		template_table.delete_item(Key={'template_id': template_id})

		duration_ms = (time.time() - start_time) * 1000
		logger.info("Template deleted", template_id=template_id, user_id=user_id, duration_ms=duration_ms)

		return {
			"statusCode": 200,
			"body": json.dumps({"message": "Template deleted successfully"}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	except Exception as e:
		log_exception(logger, "Failed to delete template", e)
		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Failed to delete template", "error": str(e)}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}
	finally:
		logger.clear_context()


# Automatic result cleanup handler
def cleanup_old_results_handler(event, context):
	"""
	Scheduled function to clean up old job results from S3 based on retention policy.
	Runs daily and deletes results older than the configured retention period.
	"""
	start_time = time.time()
	log_lambda_invocation(event, context, logger)

	try:
		# Default retention period in days (can be overridden per job)
		default_retention_days = 365

		# Get all jobs
		response = job_table.scan()
		jobs = response.get('Items', [])

		deleted_count = 0
		skipped_count = 0
		error_count = 0

		for job in jobs:
			try:
				job_id = job['job_id']

				# Check if job has custom retention setting (default to 365 days)
				retention_days = job.get('retention_days', default_retention_days)

				# Skip if retention is set to 0 (never delete)
				if retention_days == 0:
					logger.info("Skipping job with never-delete retention", job_id=job_id)
					skipped_count += 1
					continue

				# Check last_run timestamp
				last_run_str = job.get('last_run')
				if not last_run_str:
					# No results yet, skip
					skipped_count += 1
					continue

				# Parse last_run timestamp
				last_run = datetime.fromisoformat(last_run_str.replace('Z', '+00:00'))

				# Calculate age in days
				age_days = (datetime.now(timezone.utc) - last_run).days

				# Delete if older than retention period
				if age_days > retention_days:
					s3_key = f'jobs/{job_id}/result.json'

					try:
						# Check if file exists before attempting delete
						s3.head_object(Bucket=os.environ['S3_BUCKET'], Key=s3_key)

						# Delete the result file
						s3.delete_object(Bucket=os.environ['S3_BUCKET'], Key=s3_key)

						# Clear results_s3_key from job record
						job_table.update_item(
							Key={'job_id': job_id},
							UpdateExpression='REMOVE results_s3_key',
						)

						deleted_count += 1
						logger.info("Deleted old result",
								   job_id=job_id,
								   age_days=age_days,
								   retention_days=retention_days)
					except Exception as s3_error:
						if 'Not Found' in str(s3_error) or '404' in str(s3_error):
							# File doesn't exist, skip
							skipped_count += 1
						else:
							error_count += 1
							logger.warning("Failed to delete result",
										 job_id=job_id,
										 error=str(s3_error))
				else:
					skipped_count += 1

			except Exception as job_error:
				error_count += 1
				logger.warning("Error processing job for cleanup",
							 job_id=job.get('job_id', 'unknown'),
							 error=str(job_error))
				continue

		duration_ms = (time.time() - start_time) * 1000
		logger.info("Cleanup completed",
				   total_jobs=len(jobs),
				   deleted=deleted_count,
				   skipped=skipped_count,
				   errors=error_count,
				   duration_ms=duration_ms)

		return {
			"statusCode": 200,
			"body": json.dumps({
				"message": "Cleanup completed successfully",
				"total_jobs": len(jobs),
				"deleted": deleted_count,
				"skipped": skipped_count,
				"errors": error_count
			})
		}

	except Exception as e:
		log_exception(logger, "Failed to run cleanup", e)
		return {
			"statusCode": 500,
			"body": json.dumps({"message": "Failed to run cleanup", "error": str(e)})
		}
	finally:
		logger.clear_context()

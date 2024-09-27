import boto3
import json
import os
import paramiko

from crawl_manager import get_crawl
from datetime import datetime, timedelta, timezone
from job_manager import create_job, delete_job, get_all_jobs, get_job, get_job_crawls, pause_job, process_job, refresh_job, resume_job, update_job
from urllib.parse import urlparse
from utils import decimal_to_float, detect_csv_settings, extract_token_from_event, validate_clerk_token, validate_job_data

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'us-east-2'))
job_table = dynamodb.Table(os.environ['DYNAMODB_JOBS_TABLE'])
s3 = boto3.client('s3')
sqs = boto3.client('sqs')

# Create a new job
def create_job_handler(event, context):
	print(event)
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

	try:
		user_data = validate_clerk_token(token)
	except Exception as e:
		return {
			"statusCode": 401,
			"body": json.dumps({"message": str(e)}),
			"headers": {
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
		}

	job_data = json.loads(event['body'])
	validate_job_data(job_data)  # Ensure the job request is valid
	job_data["user_id"] = user_data["sub"]
	job_id = create_job(job_data)
	return {
		"statusCode": 201,
		"body": json.dumps({"message": "Job created successfully", "job_id": job_id}),
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}

# Delete a job and cancel all associated crawls
def delete_job_handler(event, context):
	print(event)
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
	jobs = get_all_jobs()
	print(jobs)
	return {
		"statusCode": 200,
		"body": json.dumps(jobs),  # Ensure body is a JSON string
		"headers": {
			'Access-Control-Allow-Credentials': True,
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

# Process a job (Triggered by SQS)
def process_job_handler(event, context):
	print(event)
	# Process each message from SQS
	for record in event['Records']:
		job_data = json.loads(record['body'])
		job_id = job_data.get('job_id')

		print(f"Processing job {job_id}")

		# Perform job processing, e.g., scraping
		result = process_job(job_data)

		# Store the result in S3
		s3.put_object(
			Bucket=os.environ['S3_BUCKET'],
			Key=f'jobs/{job_id}/result.json',
			Body=json.dumps(result)
		)

		# Update DynamoDB with job status
		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="SET #status = :status, #last_updated = :last_updated",
			ExpressionAttributeNames={'#status': 'status', '#last_updated': 'last_updated'},
			ExpressionAttributeValues={
				':status': 'ready',
				':last_updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
			}
		)

	return {
		'statusCode': 200,
		'body': json.dumps({"message": "Job processed successfully"}),
		"headers": {
				'Access-Control-Allow-Credentials': True,
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
		last_run = datetime.strptime(last_run_str, '%Y-%m-%dT%H:%M:%SZ') if last_run_str else None

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
				# Calculate the next run time
				next_run_time = last_run + timedelta(
					hours=1 if should_run_this_hour else 0,
					minutes=5 if should_run_this_minute else 0
				)
				if current_time < next_run_time:
					print(f"Job {job['job_id']} was already run recently, skipping.")
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

# Update a job
def update_job_handler(event, context):
	print(event)
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
import json

from job_manager import create_job, delete_job, get_all_jobs, get_job, get_job_crawls, pause_job, refresh_job, resume_job, update_job
from crawl_manager import get_crawl
from utils import extract_token_from_event, validate_clerk_token, validate_job_data

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
		"body": f"Job '{job_id}' created successfully",
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
		"body": f"Job {job_id} deleted successfully",
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}

# Get the status of all jobs
def get_all_job_statuses_handler(event, context):
	jobs = get_all_jobs()
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
			"body": "Crawl not found",
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
			"body": "Job not found",
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
		"body": f"Job {job_id} paused successfully",
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
		"body": f"Job {job_id} refreshed successfully",
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
		"body": f"Job {job_id} resumed successfully",
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}
 
# Update a job
def update_job_handler(event, context):
	print(event)
	job_id = event['pathParameters']['job_id']
	job_data = json.loads(event['body'])
	validate_job_data(job_data)
	update_job(job_id, job_data)
	return {
		"statusCode": 200,
		"body": f"Job {job_id} updated successfully",
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}

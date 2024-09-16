import json

from job_manager import create_job, delete_job, get_all_jobs, get_job, get_job_crawls, pause_job, refresh_job, resume_job, update_job
from crawl_manager import get_crawl
from utils import validate_job_data

# Create a new job
def create_job(event, context):
	job_data = event['body']
	validate_job_data(job_data)  # Ensure the job request is valid
	job_id = create_job(job_data)
	return {
		"statusCode": 201,
		"body": f"Job {job_id} created successfully",
		"headers": {
				'Access-Control-Allow-Credentials': True,
				'Access-Control-Allow-Origin': '*',
				"Content-Type": "application/json"
			}
	}

# Delete a job and cancel all associated crawls
def delete_job(event, context):
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
def get_all_job_statuses(event, context):
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
def get_crawl(event, context):
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
def get_job_crawls(event, context):
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
def get_job_details(event, context):
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
def pause_job(event, context):
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
def refresh_job(event, context):
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
def resume_job(event, context):
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
def update_job(event, context):
	job_id = event['pathParameters']['job_id']
	job_data = event['body']
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

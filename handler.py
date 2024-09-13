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
		"body": f"Job {job_id} created successfully"
	}

# Delete a job and cancel all associated crawls
def delete_job(event, context):
	job_id = event['pathParameters']['job_id']
	delete_job(job_id)
	return {
		"statusCode": 200,
		"body": f"Job {job_id} deleted successfully"
	}

# Get the status of all jobs
def get_all_job_statuses(event, context):
	jobs = get_all_jobs()
	return {
		"statusCode": 200,
		"body": jobs
	}

# Get specific crawl details
def get_crawl(event, context):
	job_id = event['pathParameters']['job_id']
	crawl_id = event['pathParameters']['crawl_id']
	crawl = get_crawl(job_id, crawl_id)
	if crawl:
		return {
			"statusCode": 200,
			"body": crawl
		}
	else:
		return {
			"statusCode": 404,
			"body": "Crawl not found"
		}

# Get all crawls for a job
def get_job_crawls(event, context):
	site_id = event['pathParameters']['site_id']
	crawls = get_job_crawls(site_id)
	return {
		"statusCode": 200,
		"body": crawls
	}

# Get job details
def get_job_details(event, context):
	job_id = event['pathParameters']['job_id']
	job = get_job(job_id)
	if job:
		return {
			"statusCode": 200,
			"body": job
		}
	else:
		return {
			"statusCode": 404,
			"body": "Job not found"
		}

# Pause a job
def pause_job(event, context):
	job_id = event['pathParameters']['job_id']
	pause_job(job_id)
	return {
		"statusCode": 200,
		"body": f"Job {job_id} paused successfully"
	}

# Refresh a job (manual re-crawl)
def refresh_job(event, context):
	job_id = event['pathParameters']['job_id']
	refresh_job(job_id)
	return {
		"statusCode": 200,
		"body": f"Job {job_id} refreshed successfully"
	}

# Resume a job
def resume_job(event, context):
	job_id = event['pathParameters']['job_id']
	resume_job(job_id)
	return {
		"statusCode": 200,
		"body": f"Job {job_id} resumed successfully"
	}
 
# Update a job
def update_job(event, context):
	job_id = event['pathParameters']['job_id']
	job_data = event['body']
	validate_job_data(job_data)
	update_job(job_id, job_data)
	return {
		"statusCode": 200,
		"body": f"Job {job_id} updated successfully"
	}

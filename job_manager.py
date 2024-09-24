import boto3
import os
from botocore.exceptions import ClientError
from utils import decimal_to_float, parse_links_from_file, validate_job_data

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'us-east-2'))
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

# Create a new job in DynamoDB
def create_job(job_data):
	try:
		# Parse the list of URLs from the external source
		links = parse_links_from_file(job_data['file_mapping'], job_data['source'])  # Assuming 'source' is the URL to the list
		print(f"Parsed links: {links}")

		# Add the parsed links to the job data
		job_data['links'] = links

		# Assign a job_id if it doesn't exist
		job_id = job_data.get('job_id')
		if not job_id:
			import uuid
			job_data['job_id'] = str(uuid.uuid4())

		# Ensure all necessary fields are present in job_data and add defaults if needed
		job_item = {
			'user_id': job_data['user_id'],
			'job_id': job_data['job_id'],
			'name': job_data['name'],
			'rate_limit': job_data['rate_limit'],
			'source': job_data['source'],
			'file_mapping': job_data['file_mapping'],
			'scheduling': job_data.get('scheduling', None),
			'queries': job_data['queries'],
			'created_at': job_data.get('created_at', 'timestamp here'),  # Add a timestamp for when the job was created
			'status': job_data.get('status', 'pending')  # Default job status
		}

		print(f"Creating job: {job_item}")
		# Insert job data into DynamoDB
		table.put_item(Item=job_item)
		return job_data['job_id']
	except ValueError as e:
		print(f"Job validation failed: {str(e)}")
		return None
	except ClientError as e:
		print(f"Error creating job: {e.response['Error']['Message']}")
		return None

# Delete a job from DynamoDB
def delete_job(job_id):
	try:
		table.delete_item(Key={'job_id': job_id})
		return f"Job {job_id} deleted successfully."
	except ClientError as e:
		print(f"Error deleting job: {e.response['Error']['Message']}")
		return None

# Retrieve all job statuses
def get_all_jobs():
	try:
		response = table.scan()
		print(f"Retrieved jobs response: {response}")
		jobs = response.get('Items', [])
		jobs_cleaned = decimal_to_float(jobs)  # Convert Decimals
		return jobs_cleaned
	except ClientError as e:
		print(f"Error retrieving jobs: {e.response['Error']['Message']}")
		return []

# Retrieve details of a specific job
def get_job(job_id):
	try:
		response = table.get_item(Key={'job_id': job_id})
		print(f"Retrieved job response: {response}")
		return response.get('Item')
	except ClientError as e:
		print(f"Error retrieving job {job_id}: {e.response['Error']['Message']}")
		return None

# Retrieve all crawls for a specific job
def get_job_crawls(job_id):
	try:
		response = table.query(
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
		table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="set #st = :s",
			ExpressionAttributeNames={'#st': 'status'},
			ExpressionAttributeValues={':s': 'paused'}
		)
		return f"Job {job_id} paused successfully."
	except ClientError as e:
		print(f"Error pausing job: {e.response['Error']['Message']}")
		return None

# Refresh a job (re-crawl all URLs)
def refresh_job(job_id):
	"""
	Logic to manually trigger a re-crawl for a specific job.
	This function will update the job status and initiate a new crawl process.
	"""
	# Example logic to update job status and re-run the crawl
	response = table.get_item(Key={'job_id': job_id})
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
		table.put_item(Item=job_data)

		# Initiate crawling for the new list of links
		crawl_links(new_links, job_data['queries'])

		return f"Job {job_id} refreshed and crawled successfully."
	else:
		return f"Job {job_id} not found."

# Resume a job (update status to "active")
def resume_job(job_id):
	try:
		table.update_item(
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

		table.update_item(
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

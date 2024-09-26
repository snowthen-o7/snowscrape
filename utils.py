import boto3
import csv
import jwt
import os
import pandas as pd
import paramiko
import re
import requests

from botocore.exceptions import ClientError
from decimal import Decimal
from io import StringIO
from urllib.parse import urlparse

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'us-east-2'))
s3 = boto3.client('s3')
job_table = dynamodb.Table(os.environ['DYNAMODB_JOBS_TABLE'])
url_table = dynamodb.Table(os.environ['DYNAMODB_URLS_TABLE'])

def convert_cron_to_scheduling(cron_expression):
	"""
	Converts a cron expression to scheduling data.
	"""
	parts = cron_expression.split()
	if len(parts) != 5:
		raise ValueError("Invalid cron expression")

	# Parse the hour part
	hours = parts[1]
	if hours == '*':
		hours = ['Every Hour']
	else:
		hours = [int(h) for h in hours.split(',')]

	# Parse the day part
	days = parts[4]
	if days == '*':
		days = ['Every Day']
	else:
		valid_days_map = {
			'0': 'Sunday',
			'1': 'Monday',
			'2': 'Tuesday',
			'3': 'Wednesday',
			'4': 'Thursday',
			'5': 'Friday',
			'6': 'Saturday',
		}
		days = [valid_days_map[day] for day in days.split(',') if day in valid_days_map]

	return {
		'days': days,
		'hours': hours
	}

def convert_scheduling_to_cron(scheduling):
	"""
	Converts the scheduling data to a cron expression.
	"""
	days = scheduling.get('days', [])
	hours = scheduling.get('hours', [])

	# Handle "Every Day" and "Every Hour"
	if 'Every Day' not in days:
		valid_days_map = {
			'Sunday': '0',
			'Monday': '1',
			'Tuesday': '2',
			'Wednesday': '3',
			'Thursday': '4',
			'Friday': '5',
			'Saturday': '6',
		}
		day_part = '*' if not days or 'Every Day' in days else ','.join(valid_days_map[day] for day in days)

	if 'Every Hour' not in hours:
		hour_part = '*' if not hours or 'Every Hour' in hours else ','.join(str(hour) for hour in hours)

	# Cron format: minute (0), hour, day of the month (*), month (*), day of the week
	cron_expression = f"0 {hour_part} * * {day_part}"

	return cron_expression

def cron_to_seconds(cron_expression):
	"""Converts a cron expression to the equivalent interval in seconds."""
	# Implement logic to convert cron to seconds
	pass

def decimal_to_float(obj):
	if isinstance(obj, list):
		return [decimal_to_float(i) for i in obj]
	elif isinstance(obj, dict):
		return {k: decimal_to_float(v) for k, v in obj.items()}
	elif isinstance(obj, Decimal):
		return float(obj)  # Convert Decimal to float
	else:
		return obj

# Helper function to delete all URLs associated with the job
def delete_job_links(job_id):
	try:
		# Query the url_table to get all links for the given job_id
		response = url_table.query(
			KeyConditionExpression=boto3.dynamodb.conditions.Key('job_id').eq(job_id)
		)
		
		# Get the list of URLs associated with the job
		urls = response.get('Items', [])
		
		# Batch delete each URL associated with the job
		with url_table.batch_writer() as batch:
			for url_item in urls:
				batch.delete_item(
					Key={
						'job_id': job_id,
						'url': url_item['url']
					}
				)
		print(f"Deleted {len(urls)} URLs for job {job_id}.")
	
	except ClientError as e:
		print(f"Error deleting URLs for job {job_id}: {e.response['Error']['Message']}")

# Helper function to delete the S3 result file for the job
def delete_s3_result_file(job_id):
	try:
		s3.delete_object(Bucket=os.environ['S3_BUCKET'], Key=f'jobs/{job_id}/result.json')
		print(f"Deleted result file for job {job_id} from S3.")
	
	except ClientError as e:
		print(f"Error deleting result file from S3 for job {job_id}: {e.response['Error']['Message']}")

def detect_csv_settings(file_content):
	"""
	Detects the CSV settings such as delimiter, enclosure, escape characters, and headers from a file.
	"""
	sniffer = csv.Sniffer()
	
	# Detect delimiter and quoting
	sample = file_content[:1024]  # Use the first 1024 bytes for sampling
	print(f"Sample content for sniffing:\n{sample}\n")

	try:
		dialect = sniffer.sniff(sample, delimiters=[',', ';', '\t', '|'])
		# Log detailed information about the dialect detected
		print(f"Detected CSV dialect:\n"
			f"Delimiter: {dialect.delimiter}\n"
			f"Quote character: {repr(dialect.quotechar)}\n"
			f"Escape character: {repr(dialect.escapechar)}\n"
			f"Doublequote: {dialect.doublequote}\n"
			f"Skip initial space: {dialect.skipinitialspace}\n"
			f"Line terminator: {repr(dialect.lineterminator)}\n"
			f"Quoting: {dialect.quoting}\n")
	except csv.Error as e:
		print(f"Error detecting CSV dialect: {e}")
		return {
			'delimiter': ',',
			'enclosure': '"',
			'escape': '',
			'headers': []
		}

	# Read the file into a list of rows
	reader = csv.reader(StringIO(file_content), dialect)
	headers = next(reader, None)  # Assume the first row is the header

	print(f"Detected headers: {headers}\n")
	
	return {
		'delimiter': dialect.delimiter,
		'enclosure': dialect.quotechar if dialect.quotechar else '',
		'escape': dialect.escapechar if dialect.escapechar else '',
		'headers': headers
	}

def detect_url_column(headers):
	# Define a regex to match common column names for URLs (like "link" or "url")
	url_column_regex = re.compile(r'(link|url)', re.IGNORECASE)
	
	# Iterate over the headers and return the first match
	for index, header in enumerate(headers):
		if url_column_regex.search(header):
			return index  # Return the index of the matching column
	return None  # Return None if no match is found

def extract_token_from_event(event):
	headers = event.get("headers", {})
	authorization_header = headers.get("Authorization", "")
	if authorization_header.startswith("Bearer "):
		return authorization_header[len("Bearer "):]
	return None

def fetch_urls_for_job(job_id: str) -> list:
	"""
	Query DynamoDB to fetch all URLs associated with the given job_id.
	"""
	try:
		response = url_table.query(
			KeyConditionExpression=boto3.dynamodb.conditions.Key('job_id').eq(job_id)
		)
		print(f"Fetched URLs for job {job_id}: {response}")
		return response.get('Items', [])
	except ClientError as e:
		print(f"Error fetching URLs for job {job_id}: {e.response['Error']['Message']}")
		return []

def load_from_s3(bucket_name, key):
	"""Loads data from an S3 bucket."""
	import boto3
	s3 = boto3.client('s3')
	response = s3.get_object(Bucket=bucket_name, Key=key)
	return response['Body'].read()

def log_error(job_id, error_message):
	"""Logs an error for a job."""
	# This can be integrated with a logging service or simply print the error
	print(f"Job {job_id}: {error_message}")

def parse_file(file_content, delimiter=',', enclosure='"', escape='\\', url_column=0):
	"""Parses a file containing URLs and returns a list of URLs."""
	urls = []
	reader = csv.reader(file_content.splitlines(), delimiter=delimiter, quotechar=enclosure, escapechar=escape)
	for row in reader:
		if len(row) > url_column:
			urls.append(row[url_column].strip())
	return urls

def retrieve_links_from_s3(s3_key):
	"""
	Retrieve the list of links from S3 using the provided key.
	"""
	try:
		s3 = boto3.client('s3')
		response = s3.get_object(Bucket=os.environ['S3_BUCKET'], Key=s3_key)
		print(f"Retrieved links from S3: {s3_key} ({response})")
		links_content = response['Body'].read().decode('utf-8')
		links = links_content.splitlines()  # Convert the file content back to a list of links
		print(f"Links: {links}")
		return links
	except Exception as e:
		print(f"Error retrieving links from S3: {e}")
		return []

def send_job_to_queue(job_id, job_data):
	sqs = boto3.client('sqs', region_name=os.environ.get('REGION', 'us-east-2'))
	response = sqs.send_message(
		QueueUrl=os.getenv('SQS_JOB_QUEUE_URL'),
		MessageBody=str(job_data),  # You can serialize the job data as JSON
		MessageAttributes={
			'JobId': {
				'StringValue': job_id,
				'DataType': 'String'
			}
		}
	)
	return response

def validate_clerk_token(token):
	try:
		# Validate the token using the Clerk public key from environment
		decoded_token = jwt.decode(token, os.getenv('CLERK_JWT_PUBLIC_KEY'), algorithms=["RS256"])
		return decoded_token  # Return the decoded token if valid
	except jwt.ExpiredSignatureError:
		raise Exception("Token expired.")
	except jwt.InvalidTokenError:
		raise Exception("Invalid token.")

def validate_job_data(data):
	if 'name' not in data or not isinstance(data['name'], str):
		raise ValueError("Job must have a valid 'name' (string).")

	if 'rate_limit' not in data or not isinstance(data['rate_limit'], int) or not (1 <= data['rate_limit'] <= 8):
		raise ValueError("Job must have a 'rate_limit' (integer between 1 and 8).")

	if 'source' not in data or not isinstance(data['source'], str):
		raise ValueError("Job must have a valid 'source' (string).")

	if 'file_mapping' not in data or not isinstance(data['file_mapping'], dict):
		raise ValueError("Job must have a valid 'file_mapping' (object).")
	else:
		required_file_mapping_keys = ['delimiter', 'enclosure', 'escape', 'url_column']
		for key in required_file_mapping_keys:
			if key not in data['file_mapping']:
				raise ValueError(f"'file_mapping' must contain '{key}'.")

		if data['file_mapping']['delimiter'] not in [',', ';', '|', '\t']:
			raise ValueError("Invalid 'delimiter'. Must be one of ',', ';', '|', or '\t'.")
		if data['file_mapping']['enclosure'] not in ['"', "'", "none"]:
			raise ValueError("Invalid 'enclosure'. Must be either '\"', '\'', or 'none'.")
		if data['file_mapping']['escape'] not in ['\\', '/', '"', "'", "none"]:
			raise ValueError("Invalid 'escape'. Must be '\\', '/', '\"', '\'', or 'none'.")

	if 'scheduling' in data:
		if 'hours' not in data['scheduling'] or not isinstance(data['scheduling']['hours'], list):
			raise ValueError("'scheduling' must include 'hours' as a list.")
		for hour in data['scheduling']['hours']:
			if not isinstance(hour, int) or not (0 <= hour <= 24):
				raise ValueError("'hours' must be integers between 0 and 23, or 'Every Hour'.")

		if 'days' not in data['scheduling'] or not isinstance(data['scheduling']['days'], list):
			raise ValueError("'scheduling' must include 'days' as a list.")
		valid_days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Every Day']
		for day in data['scheduling']['days']:
			if day not in valid_days:
				raise ValueError(f"'days' must be one of {', '.join(valid_days)}.")

	if 'queries' not in data or not isinstance(data['queries'], list):
		raise ValueError("Job must have a 'queries' (array).")
	else:
		for query in data['queries']:
			if 'name' not in query or not isinstance(query['name'], str):
				raise ValueError("Each query must have a valid 'name' (string).")
			if 'type' not in query or query['type'] not in ['xpath', 'regex', 'jsonpath']:
				raise ValueError("Each query must have a valid 'type' (xpath, regex, or jsonpath).")
			if 'query' not in query or not isinstance(query['query'], str):
				raise ValueError("Each query must have a valid 'query' (string).")

def fetch_file_content(file_url):
	"""
	Fetches file content from HTTP/HTTPS or SFTP URLs.
	Returns file content as string.
	"""
	parsed_url = urlparse(file_url)

	if parsed_url.scheme in ['http', 'https']:
		# Fetch file from HTTP/HTTPS
		response = requests.get(file_url)
		response.raise_for_status()
		return response.text

	elif parsed_url.scheme == 'sftp':
		# Fetch file from SFTP
		if not parsed_url.username or not parsed_url.password:
				raise Exception("SFTP URL must contain a username and password")

		transport = paramiko.Transport((parsed_url.hostname, parsed_url.port or 22))
		transport.connect(username=parsed_url.username, password=parsed_url.password)
		sftp = paramiko.SFTPClient.from_transport(transport)

		try:
			with sftp.file(parsed_url.path, 'r') as remote_file:
				file_content = remote_file.read().decode('utf-8')  # Read and decode bytes to string
		finally:
			sftp.close()
			transport.close()

		return file_content

	else:
		raise Exception("Unsupported URL scheme. Only HTTP, HTTPS, and SFTP are supported.")

def parse_links_from_file(file_mapping, file_url):
	try:
		# Fetch file content from the given URL (HTTP/HTTPS or SFTP)
		file_content = fetch_file_content(file_url)

		# Step 1: Try using pandas to autodetect CSV structure and extract links
		df = pd.read_csv(StringIO(file_content), on_bad_lines="skip")  # Using StringIO to treat file content as a file-like object
		
		# Handle the "default" option for URL column
		if file_mapping['url_column'] == 'default':
			url_column_index = detect_url_column(df.columns)  # Use the regex to detect a matching column
			if url_column_index is None:
				raise ValueError("No suitable URL column found matching 'link' or 'url'.")
			url_column = df.columns[url_column_index]  # Use the detected column
		else:
			# If 'url_column' is a string, use it as a column name. If it's an integer, use it as an index.
			url_column = file_mapping['url_column'] if isinstance(file_mapping['url_column'], str) else df.columns[file_mapping['url_column']]
		
		# Extract the URLs from the specified column
		urls = df[url_column].dropna().tolist()
  
		print("Pandas auto-detection successful.")
		print(urls)
		return urls

	except Exception as e:
		# Step 2: If pandas fails, fallback to csv with manual file_mapping settings
		print(f"Pandas failed to parse file. Falling back to manual parsing. Error: {e}")
		print(file_mapping)

		# Manual parsing using csv.reader
		delimiter = file_mapping.get('delimiter', ',')
		quotechar = None if file_mapping.get('enclosure') == 'none' else file_mapping.get('enclosure', None)
		escapechar = None if file_mapping.get('escape') == 'none' else file_mapping.get('escape', None)
		
		reader = csv.reader(file_content.splitlines(), delimiter=delimiter, quotechar=quotechar, escapechar=escapechar)
		
		links = []
		url_column_index = None  # Initialize the url_column_index variable

		for row_num, row in enumerate(reader):
			# Handle the first row (header) if url_column is a string (header name)
			if row_num == 0 and isinstance(file_mapping['url_column'], str):
				if file_mapping['url_column'] in row:
					url_column_index = row.index(file_mapping['url_column'])  # Find the index of the header
				else:
					raise Exception(f"Column '{file_mapping['url_column']}' not found in header")
			elif isinstance(file_mapping['url_column'], int):
				url_column_index = file_mapping['url_column']  # Use the integer as the column index

			# Ensure url_column_index is set and the row has enough columns
			if url_column_index is not None and len(row) > url_column_index:
				links.append(row[url_column_index].strip())
						
		return links

def update_url_status(job_id: str, url: str, status: str) -> None:
	"""
	Update the status of a URL in the url_table.
	
	Args:
	- job_id (str): The ID of the job the URL is associated with.
	- url (str): The URL being updated.
	- status (str): The new status for the URL.
	"""
	try:
		url_table.update_item(
			Key={'job_id': job_id, 'url': url},
			UpdateExpression="SET #status = :status",
			ExpressionAttributeNames={'#status': 'status'},
			ExpressionAttributeValues={':status': status}
		)
		print(f"Updated URL {url} status to {status}.")
	except ClientError as e:
		print(f"Error updating status for URL {url}: {e.response['Error']['Message']}")
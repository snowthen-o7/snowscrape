import boto3
import csv
import json
import jwt
import os
import random
import re
import requests

# Optional imports - used only for specific features
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from connection_pool import get_table, get_s3_client
from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO
from requests.sessions import Session
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from logger import get_logger
from url_variable_resolver import URLVariableResolver
from validators import validate_scrape_url, ValidationError as ScrapeValidationError

logger = get_logger(__name__)

# Use connection pool for AWS services
s3 = get_s3_client()
job_table = get_table(os.environ['DYNAMODB_JOBS_TABLE'])
url_table = get_table(os.environ['DYNAMODB_URLS_TABLE'])

# Define a list of common user agents and referrers
REFERRERS = [
	"https://www.google.com",
	"https://www.bing.com",
	"https://duckduckgo.com",
	# Add more referrers if needed
]

USER_AGENTS = [
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
	"Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36",
	# Add more user agents if needed
]

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
	"""
	Converts a simple cron expression to the equivalent interval in seconds.

	Supports basic periodic cron expressions like:
	- "0 * * * *" (every hour) -> 3600
	- "0 0 * * *" (every day) -> 86400
	- "*/15 * * * *" (every 15 minutes) -> 900

	Args:
		cron_expression (str): Cron expression in format "minute hour day month weekday"

	Returns:
		int: Interval in seconds, or None if expression cannot be converted
	"""
	if not cron_expression:
		return None

	parts = cron_expression.strip().split()
	if len(parts) != 5:
		logger.warning("Invalid cron expression format", cron_expression=cron_expression)
		return None

	minute, hour, day, month, weekday = parts

	try:
		# Handle simple periodic patterns
		# Pattern: "0 * * * *" = every hour
		if minute == "0" and hour == "*":
			return 3600  # 1 hour

		# Pattern: "0 0 * * *" = every day
		if minute == "0" and hour == "0":
			return 86400  # 24 hours

		# Pattern: "*/N * * * *" = every N minutes
		if minute.startswith("*/"):
			interval = int(minute.split("/")[1])
			return interval * 60

		# Pattern: "0 */N * * *" = every N hours
		if hour.startswith("*/") and minute == "0":
			interval = int(hour.split("/")[1])
			return interval * 3600

		# If specific minute and hour are set, treat as daily
		if minute.isdigit() and hour.isdigit():
			return 86400  # Daily

		logger.warning("Cron expression pattern not supported for interval conversion", cron_expression=cron_expression)
		return None

	except (ValueError, IndexError) as e:
		logger.error("Error parsing cron expression", cron_expression=cron_expression, error=str(e))
		return None

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
		logger.info("Deleted URLs for job", job_id=job_id, url_count=len(urls))
	
	except ClientError as e:
		logger.error("Error deleting URLs for job", job_id=job_id, error=e.response['Error']['Message'])

# Helper function to delete the S3 result file for the job
def delete_s3_result_file(job_id):
	try:
		s3.delete_object(Bucket=os.environ['S3_BUCKET'], Key=f'jobs/{job_id}/result.json')
		logger.info("Deleted result file from S3", job_id=job_id)
	
	except ClientError as e:
		logger.error("Error deleting result file from S3", job_id=job_id, error=e.response['Error']['Message'])

def detect_csv_settings(file_content):
	"""
	Detects the CSV settings such as delimiter, enclosure, escape characters, and headers from a file.
	"""
	sniffer = csv.Sniffer()
	
	# Detect delimiter and quoting
	sample = file_content[:1024]  # Use the first 1024 bytes for sampling
	logger.debug("Sample content for sniffing", sample_length=len(sample))

	try:
		dialect = sniffer.sniff(sample, delimiters=[',', ';', '\t', '|'])
		# Log detailed information about the dialect detected
		logger.debug("Detected CSV dialect", delimiter=dialect.delimiter, quotechar=repr(dialect.quotechar), escapechar=repr(dialect.escapechar), doublequote=dialect.doublequote, skipinitialspace=dialect.skipinitialspace, quoting=dialect.quoting)
	except csv.Error as e:
		logger.error("Error detecting CSV dialect", error=str(e))
		return {
			'delimiter': ',',
			'enclosure': '"',
			'escape': '',
			'headers': []
		}

	# Read the file into a list of rows
	reader = csv.reader(StringIO(file_content), dialect)
	headers = next(reader, None)  # Assume the first row is the header

	logger.debug("Detected headers", header_count=len(headers) if headers else 0)
	
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
	# API Gateway V2 lowercases all header names
	authorization_header = headers.get("authorization") or headers.get("Authorization") or ""
	if authorization_header.startswith("Bearer "):
		return authorization_header[len("Bearer "):]
	return None

# Use this function for each URL request, and pass the session across requests within the job
def fetch_url_with_session(url: str, session: Session, job_id: str, proxy_config: dict = None, render_config: dict = None) -> dict:
	"""
	Fetches the URL using the provided session with optional proxy retry logic and JS rendering.

	Args:
	- url: The URL to scrape.
	- session: The requests.Session object.
	- job_id: The job ID for logging or tracking.
	- proxy_config: Optional. Proxy configuration for retry logic.
	- render_config: Optional. JavaScript rendering configuration.

	Returns:
	- dict: Contains the status and response content or error message.
	"""
	from proxy_manager import get_proxy_manager
	import time
	import boto3

	# SSRF protection: validate URL before making any request
	try:
		validate_scrape_url(url)
	except ScrapeValidationError as e:
		logger.warning("SSRF protection blocked URL", job_id=job_id, url=url, error=str(e))
		return {"status": "error", "message": f"URL validation failed: {str(e)}"}

	# Check if JavaScript rendering is enabled
	if render_config and render_config.get('enabled'):
		try:
			logger.info("Using JavaScript rendering", job_id=job_id, url=url)

			# Get proxy URL if proxy is enabled
			proxy_url = None
			if proxy_config and proxy_config.get('enabled') and session.proxies:
				proxy_url = session.proxies.get('http') or session.proxies.get('https')

			# Prepare render config for Lambda
			lambda_render_config = {
				'wait_strategy': render_config.get('wait_strategy', 'networkidle'),
				'wait_timeout_ms': render_config.get('wait_timeout_ms', 30000),
				'wait_for_selector': render_config.get('wait_for_selector'),
				'viewport': render_config.get('viewport', {'width': 1920, 'height': 1080}),
				'capture_screenshot': render_config.get('capture_screenshot', False),
				'screenshot_full_page': render_config.get('screenshot_full_page', False),
				'block_resources': render_config.get('block_resources', []),
				'user_agent': session.headers.get('User-Agent'),
				'proxy_url': proxy_url
			}

			# Invoke JS renderer Lambda
			lambda_client = boto3.client('lambda')
			response = lambda_client.invoke(
				FunctionName='snowscrape-js-renderer',
				InvocationType='RequestResponse',
				Payload=json.dumps({
					'url': url,
					'render_config': lambda_render_config
				})
			)

			# Parse response
			result = json.loads(response['Payload'].read())
			body = json.loads(result.get('body', '{}'))

			if body.get('status') == 'success':
				logger.info("JavaScript rendering successful", job_id=job_id, url=url)
				return {
					'status': 'success',
					'content': body['content'].encode('utf-8'),
					'http_code': 200,
					'content_type': body.get('content_type', 'text/html')
				}
			else:
				error_msg = body.get('error', 'Unknown rendering error')
				logger.warning("JavaScript rendering failed", job_id=job_id, url=url, error=error_msg)

				# Fallback to standard request if configured
				if render_config.get('fallback_to_standard', True):
					logger.info("Falling back to standard request", job_id=job_id)
				else:
					return {'status': 'error', 'message': f"JS rendering failed: {error_msg}"}

		except Exception as e:
			logger.error("Error invoking JS renderer", job_id=job_id, error=str(e))

			# Fallback to standard request if configured
			if not render_config.get('fallback_to_standard', True):
				return {'status': 'error', 'message': f"JS renderer invocation failed: {str(e)}"}

	# Standard request logic (or fallback from JS rendering)
	max_retries = proxy_config.get('max_retries', 3) if proxy_config and proxy_config.get('enabled') else 1

	for attempt in range(max_retries):
		try:
			logger.info("Fetching URL", job_id=job_id, url=url, attempt=attempt + 1, max_retries=max_retries)
			response = session.get(url, timeout=30)

			# Success - status code < 400
			if response.status_code < 400:
				logger.info("Successfully fetched URL", job_id=job_id, url=url)

				# Track proxy usage if using proxy
				if proxy_config and proxy_config.get('enabled') and session.proxies:
					try:
						proxy_manager = get_proxy_manager()
						proxy_url = session.proxies.get('http') or session.proxies.get('https')
						content_length = len(response.content) if response.content else 0
						proxy_manager.track_usage(proxy_url, success=True, bytes_transferred=content_length)
					except Exception as e:
						logger.warning("Failed to track proxy usage", job_id=job_id, error=str(e))

				return {"status": "success", "content": response.content, "http_code": response.status_code, "content_type": response.headers.get('Content-Type', '')}

			# Proxy errors - rotate and retry
			if response.status_code in [407, 502, 504] and attempt < max_retries - 1:
				logger.warning("Proxy error, rotating proxy", job_id=job_id, http_code=response.status_code)

				if proxy_config and proxy_config.get('enabled'):
					try:
						# Mark current proxy as failed
						if session.proxies:
							proxy_manager = get_proxy_manager()
							proxy_url = session.proxies.get('http') or session.proxies.get('https')
							proxy_manager.mark_proxy_failed(proxy_url, f"HTTP {response.status_code}")

						# Get new proxy
						proxy_manager = get_proxy_manager()
						new_proxy = proxy_manager.get_proxy_url(proxy_config)

						if new_proxy:
							session.proxies = {'http': new_proxy, 'https': new_proxy}
							logger.info("Rotated to new proxy", job_id=job_id)
							time.sleep(2 ** attempt)
							continue
					except Exception as e:
						logger.error("Failed to rotate proxy", job_id=job_id, error=str(e))

			# Other HTTP errors
			return {"status": "error", "message": f"HTTP {response.status_code}", "http_code": response.status_code}

		except requests.exceptions.Timeout:
			logger.warning("Request timeout", job_id=job_id, url=url)

			# Mark proxy as failed
			if proxy_config and proxy_config.get('enabled') and session.proxies:
				try:
					proxy_manager = get_proxy_manager()
					proxy_url = session.proxies.get('http') or session.proxies.get('https')
					proxy_manager.mark_proxy_failed(proxy_url, "Timeout")
				except Exception as e:
					logger.warning("Failed to mark proxy as failed", job_id=job_id, error=str(e))

			if attempt < max_retries - 1:
				time.sleep(2 ** attempt)
				continue

			return {"status": "error", "message": "Request timeout"}

		except requests.RequestException as e:
			logger.error("Error fetching URL", job_id=job_id, url=url, error=str(e))

			# Mark proxy as failed
			if proxy_config and proxy_config.get('enabled') and session.proxies:
				try:
					proxy_manager = get_proxy_manager()
					proxy_url = session.proxies.get('http') or session.proxies.get('https')
					proxy_manager.mark_proxy_failed(proxy_url, str(e))
				except Exception:
					pass

			if attempt < max_retries - 1:
				time.sleep(2 ** attempt)
				continue

			return {"status": "error", "message": str(e)}

	return {"status": "error", "message": "Max retries exceeded"}

def fetch_urls_for_job(job_id: str) -> list:
	"""
	Query DynamoDB to fetch all URLs associated with the given job_id.
	"""
	try:
		response = url_table.query(
			KeyConditionExpression=boto3.dynamodb.conditions.Key('job_id').eq(job_id)
		)
		logger.debug("Fetched URLs for job", job_id=job_id, url_count=len(response.get('Items', [])))
		return response.get('Items', [])
	except ClientError as e:
		logger.error("Error fetching URLs for job", job_id=job_id, error=e.response['Error']['Message'])
		return []

# This utility function initializes a session, rotates user agents, referrers, and manages session cookies.
def initialize_session(job_id: str, session_data: dict = None, proxy_config: dict = None) -> Session:
	"""
	Initialize a session with random user agent, referrer, proxy (optional), and session data.

	Args:
	- job_id: The job ID associated with this session.
	- session_data: Optional. Contains user agent, referrer, and cookies from previous requests.
	- proxy_config: Optional. Proxy configuration dict with:
		- enabled: bool
		- geo_targeting: str ('us', 'eu', 'as', 'any')
		- rotation_strategy: str ('random', 'round-robin')
		- fallback_to_direct: bool

	Returns:
	- A tuple (session, session_data) with configured requests.Session object
	"""
	from proxy_manager import get_proxy_manager

	session = Session()

	# Rotate or reuse user agent and referrer
	if session_data:
		user_agent = session_data.get("user_agent")
		referrer = session_data.get("referrer")
		cookies = session_data.get("cookies")

		# If there are previous cookies, reuse them
		if cookies:
			session.cookies.update(cookies)
	else:
		# Randomly select a new user agent and referrer
		user_agent = random.choice(USER_AGENTS)
		referrer = random.choice(REFERRERS)

	headers = {
		"User-Agent": user_agent,
		"Referer": referrer,
	}
	session.headers.update(headers)

	# Configure proxy if enabled
	if proxy_config and proxy_config.get('enabled'):
		try:
			proxy_manager = get_proxy_manager()
			proxy_url = proxy_manager.get_proxy_url(proxy_config)

			if proxy_url:
				session.proxies = {
					'http': proxy_url,
					'https': proxy_url
				}
				session.verify = True
				logger.info("Session configured with proxy", job_id=job_id)
			elif proxy_config.get('fallback_to_direct', True):
				logger.info("No proxy available, using direct connection", job_id=job_id)
			else:
				raise Exception("No proxy available and fallback disabled")
		except Exception as e:
			logger.error("Error configuring proxy", job_id=job_id, error=str(e))
			if not proxy_config.get('fallback_to_direct', True):
				raise

	# Save session data for reuse in future calls within the same job
	session_data = {
		"user_agent": user_agent,
		"referrer": referrer,
		"cookies": session.cookies.get_dict()  # Store session cookies
	}

	return session, session_data

def load_from_s3(bucket_name, key):
	"""Loads data from an S3 bucket."""
	import boto3
	s3 = boto3.client('s3')
	response = s3.get_object(Bucket=bucket_name, Key=key)
	return response['Body'].read()

def log_error(job_id, error_message):
	"""Logs an error for a job."""
	# This can be integrated with a logging service or simply print the error
	logger.error("Job error", job_id=job_id, error=error_message)

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
		logger.debug("Retrieved links from S3", s3_key=s3_key)
		links_content = response['Body'].read().decode('utf-8')
		links = links_content.splitlines()  # Convert the file content back to a list of links
		logger.debug("Links retrieved", link_count=len(links))
		return links
	except Exception as e:
		logger.error("Error retrieving links from S3", error=str(e))
		return []

def save_results_to_s3(results, job_id):
	"""
	Save the final job results to S3 as a consolidated file.
	"""
	s3 = boto3.client('s3')
	s3_key = f"jobs/{job_id}/results.json"
	try:
		s3.put_object(
			Bucket=os.environ['S3_BUCKET'],
			Key=s3_key,
			Body=json.dumps(results)
		)
		logger.info("Results successfully saved to S3", s3_key=s3_key)
		return s3_key
	except Exception as e:
		logger.error("Error saving results to S3", error=str(e))
		return None

def save_session_data(job_id: str, session_data: Dict[str, Any]) -> None:
	"""
	Save the session data (e.g., cookies, user agent, referrer) for a job to DynamoDB.
	
	Args:
	- job_id (str): The ID of the job whose session data is being saved.
	- session_data (dict): A dictionary containing session data (cookies, user agents, etc.).
	"""
	try:
		dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'us-east-2'))
		session_table = dynamodb.Table(os.environ['DYNAMODB_SESSION_TABLE'])

		session_table.put_item(
			Item={
				'job_id': job_id,
				'session_data': session_data,
				'last_updated': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
			}
		)
		logger.info("Session data saved successfully", job_id=job_id)
	except Exception as e:
		logger.error("Error saving session data", job_id=job_id, error=str(e))

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


def verify_resource_ownership(resource: dict, user_id: str, resource_type: str = 'resource') -> None:
	"""
	Verify the authenticated user owns this resource.
	Raises PermissionError if the resource does not belong to the user.

	Args:
		resource: The resource dict (job, template, webhook, etc.)
		user_id: The authenticated user's ID (from JWT 'sub' claim)
		resource_type: Human-readable resource type for error messages
	"""
	if resource.get('user_id') != user_id:
		raise PermissionError(f"You do not have permission to access this {resource_type}")

def validate_job_data(data):
	"""
	Validate job data using comprehensive validators.
	This function provides backward compatibility with the original validation
	while using the new validators module for enhanced security.
	"""
	from validators import validate_job_data_strict, ValidationError as ValidatorError

	try:
		# Use the strict validator which provides comprehensive validation
		validated_data = validate_job_data_strict(data)

		# Additional scheduling validation (if present)
		if 'scheduling' in data and data['scheduling'] is not None:
			scheduling = data['scheduling']

			if 'hours' not in scheduling or not isinstance(scheduling['hours'], list):
				raise ValueError("'scheduling' must include 'hours' as a list.")
			for hour in scheduling['hours']:
				if not isinstance(hour, int) or not (0 <= hour <= 24):
					raise ValueError("'hours' must be integers between 0 and 23, or 24 for 'Every Hour'.")

			if 'days' not in scheduling or not isinstance(scheduling['days'], list):
				raise ValueError("'scheduling' must include 'days' as a list.")
			valid_days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Every Day']
			for day in scheduling['days']:
				if day not in valid_days:
					raise ValueError(f"'days' must be one of {', '.join(valid_days)}.")

	except ValidatorError as e:
		# Convert ValidationError to ValueError for backward compatibility
		raise ValueError(str(e))

def fetch_file_content(file_url):
	"""
	Fetches file content from HTTP/HTTPS or SFTP URLs.
	Returns file content as string.
	"""
	parsed_url = urlparse(file_url)

	if parsed_url.scheme in ['http', 'https']:
		# SSRF protection: validate URL before fetching
		try:
			validate_scrape_url(file_url)
		except ScrapeValidationError as e:
			raise Exception(f"URL validation failed (SSRF protection): {str(e)}")

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

		# Step 1: Try using pandas to autodetect CSV structure and extract links (if available)
		if not PANDAS_AVAILABLE:
			raise ImportError("Pandas not available, using fallback CSV parser")
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
  
		logger.info("Pandas auto-detection successful", url_count=len(urls))
		return urls

	except Exception as e:
		# Step 2: If pandas fails, fallback to csv with manual file_mapping settings
		logger.warning("Pandas failed to parse file, falling back to manual parsing", error=str(e))

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

def refresh_job_urls(job_id, links):
	"""
	Refresh the URLs for a given job in the URL table.
	If the job already has URLs, they will be replaced with the new links.
	"""
	try:
		# First, delete existing URLs for the job
		existing_urls = url_table.query(
			KeyConditionExpression=Key('job_id').eq(job_id)
		).get('Items', [])

		with url_table.batch_writer() as batch:
			for url_item in existing_urls:
				batch.delete_item(Key={'job_id': job_id, 'url': url_item['url']})

		# Now, insert the refreshed links into the URL table with state 'ready'
		with url_table.batch_writer() as batch:
			for url in links:
				batch.put_item(Item={
					'job_id': job_id,
					'url': url,
					'state': 'ready',
					'last_updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
				})

		logger.info("Successfully refreshed URLs for job", job_id=job_id)
	except Exception as e:
		logger.error("Error refreshing URLs for job", job_id=job_id, error=str(e))


def resolve_direct_url(url_template: str, exec_time: Optional[datetime] = None, tz: Optional[str] = None) -> str:
	"""
	Resolve a URL template with dynamic variables.

	Supports PHP-style date format variables:
	- {{date}} -> 2026-01-22 (default Y-m-d format)
	- {{date:Y-m-d}} -> 2026-01-22
	- {{date:m/d/Y}} -> 01/22/2026
	- {{date+1d:Y-m-d}} -> tomorrow's date
	- {{date-1d:Y-m-d}} -> yesterday's date
	- {{time:H_i}} -> 20_00

	Args:
		url_template: URL template containing {{date}} or {{time}} variables
		exec_time: Optional datetime for resolution (defaults to current UTC time)
		tz: Optional timezone name (e.g., 'America/New_York'). If None, uses UTC.

	Returns:
		The resolved URL with all variables replaced
	"""
	if exec_time is None:
		exec_time = datetime.now(timezone.utc)

	return URLVariableResolver.resolve(url_template, exec_time, tz)


def get_links_for_job(job_data: dict, exec_time: Optional[datetime] = None) -> List[str]:
	"""
	Get links for a job based on its source type.

	Supports two source types:
	- 'csv': Parse URLs from a CSV file (traditional mode)
	- 'direct_url': Use a single URL template with optional variables

	Args:
		job_data: Job configuration dictionary containing source_type and either
		          source (for CSV) or url_template (for direct URL)
		exec_time: Optional datetime for variable resolution

	Returns:
		List of URLs to process
	"""
	source_type = job_data.get('source_type', 'csv')

	if source_type == 'direct_url':
		# Direct URL mode - resolve template and return single URL
		url_template = job_data.get('url_template', '')
		if not url_template:
			raise ValueError("url_template is required for direct_url source type")

		# Get timezone from job data
		tz = job_data.get('timezone')

		resolved_url = resolve_direct_url(url_template, exec_time, tz)
		logger.info("Resolved URL template", url_template=url_template, resolved_url=resolved_url, timezone=tz or 'UTC')
		return [resolved_url]

	else:
		# CSV mode - parse URLs from source file
		source = job_data.get('source', '')
		file_mapping = job_data.get('file_mapping', {})

		if not source:
			raise ValueError("source is required for csv source type")

		return parse_links_from_file(file_mapping, source)


def preview_url_template(url_template: str, exec_time: Optional[datetime] = None, tz: Optional[str] = None) -> dict:
	"""
	Preview a URL template resolution without creating a job.

	Args:
		url_template: URL template to preview
		exec_time: Optional datetime for resolution
		tz: Optional timezone name (e.g., 'America/New_York'). If None, uses UTC.

	Returns:
		Dictionary with preview information including resolved URL and variables
	"""
	return URLVariableResolver.preview(url_template, exec_time, tz)


def get_common_timezones() -> List[str]:
	"""
	Get list of common timezones for UI dropdown.

	Returns:
		List of timezone strings
	"""
	return URLVariableResolver.get_common_timezones()

def update_job_status(job_id: str, status: str) -> None:
	"""
	Update the status of a job in the DynamoDB job table.
	
	Args:
	- job_id (str): The ID of the job to update.
	- status (str): The new status of the job (e.g., 'in progress', 'finished', 'error').
	"""
	try:
		dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'us-east-2'))
		job_table = dynamodb.Table(os.environ['DYNAMODB_JOBS_TABLE'])
		
		job_table.update_item(
			Key={'job_id': job_id},
			UpdateExpression="SET #status = :status, #last_updated = :last_updated",
			ExpressionAttributeNames={
				'#status': 'status',
				'#last_updated': 'last_updated'
			},
			ExpressionAttributeValues={
				':status': status,
				':last_updated': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
			}
		)
		logger.info("Job status updated", job_id=job_id, status=status)
	except Exception as e:
		logger.error("Error updating job status", job_id=job_id, error=str(e))

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
		logger.debug("Updated URL status", url=url, status=status)
	except ClientError as e:
		logger.error("Error updating URL status", url=url, error=e.response['Error']['Message'])
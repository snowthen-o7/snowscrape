import json
import os
import pytest
from datetime import datetime, timezone
from moto import mock_aws


@pytest.fixture(scope='function')
def aws_credentials():
	"""Mock AWS credentials for moto."""
	os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
	os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
	os.environ['AWS_SECURITY_TOKEN'] = 'testing'
	os.environ['AWS_SESSION_TOKEN'] = 'testing'
	os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'


@pytest.fixture(scope='function')
def mock_env_vars():
	"""Set up mock environment variables for testing."""
	os.environ['DYNAMODB_JOBS_TABLE'] = 'SnowscrapeJobs-test'
	os.environ['DYNAMODB_SESSION_TABLE'] = 'SnowscrapeSessions-test'
	os.environ['DYNAMODB_URLS_TABLE'] = 'SnowscrapeUrls-test'
	os.environ['S3_BUCKET'] = 'snowscrape-results-test'
	os.environ['SQS_JOB_QUEUE'] = 'SnowscrapeJobQueue-test'
	os.environ['SQS_JOB_QUEUE_URL'] = 'https://sqs.us-east-2.amazonaws.com/test/SnowscrapeJobQueue-test'
	os.environ['REGION'] = 'us-east-2'
	os.environ['CLERK_JWT_PUBLIC_KEY'] = 'test-public-key'
	os.environ['CLERK_JWT_SECRET_KEY'] = 'test-secret-key'

	yield

	# Cleanup
	for key in ['DYNAMODB_JOBS_TABLE', 'DYNAMODB_SESSION_TABLE', 'DYNAMODB_URLS_TABLE',
				'S3_BUCKET', 'SQS_JOB_QUEUE', 'SQS_JOB_QUEUE_URL', 'REGION',
				'CLERK_JWT_PUBLIC_KEY', 'CLERK_JWT_SECRET_KEY']:
		if key in os.environ:
			del os.environ[key]


@pytest.fixture(scope='function')
def dynamodb_client(aws_credentials, mock_env_vars):
	"""Create a mock DynamoDB client."""
	with mock_aws():
		import boto3
		dynamodb = boto3.resource('dynamodb', region_name='us-east-2')

		# Create test tables
		# Jobs table
		dynamodb.create_table(
			TableName='SnowscrapeJobs-test',
			KeySchema=[
				{'AttributeName': 'job_id', 'KeyType': 'HASH'}
			],
			AttributeDefinitions=[
				{'AttributeName': 'job_id', 'AttributeType': 'S'},
				{'AttributeName': 'status', 'AttributeType': 'S'}
			],
			GlobalSecondaryIndexes=[
				{
					'IndexName': 'StatusIndex',
					'KeySchema': [
						{'AttributeName': 'status', 'KeyType': 'HASH'}
					],
					'Projection': {'ProjectionType': 'ALL'}
				}
			],
			BillingMode='PAY_PER_REQUEST'
		)

		# Sessions table
		dynamodb.create_table(
			TableName='SnowscrapeSessions-test',
			KeySchema=[
				{'AttributeName': 'job_id', 'KeyType': 'HASH'}
			],
			AttributeDefinitions=[
				{'AttributeName': 'job_id', 'AttributeType': 'S'}
			],
			BillingMode='PAY_PER_REQUEST'
		)

		# URLs table
		dynamodb.create_table(
			TableName='SnowscrapeUrls-test',
			KeySchema=[
				{'AttributeName': 'job_id', 'KeyType': 'HASH'},
				{'AttributeName': 'url', 'KeyType': 'RANGE'}
			],
			AttributeDefinitions=[
				{'AttributeName': 'job_id', 'AttributeType': 'S'},
				{'AttributeName': 'url', 'AttributeType': 'S'},
				{'AttributeName': 'status', 'AttributeType': 'S'}
			],
			GlobalSecondaryIndexes=[
				{
					'IndexName': 'StatusIndex',
					'KeySchema': [
						{'AttributeName': 'status', 'KeyType': 'HASH'}
					],
					'Projection': {'ProjectionType': 'ALL'}
				}
			],
			BillingMode='PAY_PER_REQUEST'
		)

		yield dynamodb


@pytest.fixture(scope='function')
def s3_client(aws_credentials, mock_env_vars):
	"""Create a mock S3 client."""
	with mock_aws():
		import boto3
		s3 = boto3.client('s3', region_name='us-east-2')

		# Create test bucket
		s3.create_bucket(
			Bucket='snowscrape-results-test',
			CreateBucketConfiguration={'LocationConstraint': 'us-east-2'}
		)

		yield s3


@pytest.fixture(scope='function')
def sqs_client(aws_credentials, mock_env_vars):
	"""Create a mock SQS client."""
	with mock_aws():
		import boto3
		sqs = boto3.client('sqs', region_name='us-east-2')

		# Create test queue
		sqs.create_queue(QueueName='SnowscrapeJobQueue-test')

		yield sqs


@pytest.fixture
def sample_job_data():
	"""Provide sample job data for testing."""
	return {
		'job_id': 'test-job-123',
		'name': 'Test Job',
		'user_id': 'user-123',
		'source': 'https://example.com/urls.csv',
		'file_mapping': {
			'delimiter': ',',
			'enclosure': '"',
			'escape': '\\',
			'url_column': 0
		},
		'queries': [
			{
				'name': 'title',
				'type': 'xpath',
				'selector': '//title/text()',
				'join': False
			},
			{
				'name': 'price',
				'type': 'regex',
				'selector': r'\$(\d+\.\d{2})',
				'join': False
			}
		],
		'rate_limit': 1,
		'scheduling': None,
		'status': 'ready',
		'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
	}


@pytest.fixture
def sample_url_data():
	"""Provide sample URL data for testing."""
	return [
		{
			'job_id': 'test-job-123',
			'url': 'https://example.com/page1',
			'state': 'ready',
			'last_updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
		},
		{
			'job_id': 'test-job-123',
			'url': 'https://example.com/page2',
			'state': 'ready',
			'last_updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
		}
	]


@pytest.fixture
def sample_html_content():
	"""Provide sample HTML content for testing."""
	return """
	<!DOCTYPE html>
	<html>
	<head>
		<title>Test Page</title>
	</head>
	<body>
		<h1>Sample Product</h1>
		<div class="price">$99.99</div>
		<p class="description">This is a test product</p>
		<ul id="features">
			<li>Feature 1</li>
			<li>Feature 2</li>
			<li>Feature 3</li>
		</ul>
	</body>
	</html>
	"""


@pytest.fixture
def sample_json_content():
	"""Provide sample JSON content for testing."""
	return {
		'product': {
			'name': 'Test Product',
			'price': 99.99,
			'features': ['Feature 1', 'Feature 2', 'Feature 3'],
			'metadata': {
				'manufacturer': 'Test Corp',
				'sku': 'TEST-123'
			}
		}
	}


@pytest.fixture
def lambda_context():
	"""Mock Lambda context object."""
	class LambdaContext:
		def __init__(self):
			self.function_name = 'test-function'
			self.function_version = '1'
			self.invoked_function_arn = 'arn:aws:lambda:us-east-2:123456789012:function:test-function'
			self.memory_limit_in_mb = 128
			self.aws_request_id = 'test-request-id'
			self.log_group_name = '/aws/lambda/test-function'
			self.log_stream_name = 'test-stream'

		def get_remaining_time_in_millis(self):
			return 30000

	return LambdaContext()

"""
Connection pooling and caching utilities for AWS services and HTTP sessions.
Optimizes Lambda function performance by reusing connections across invocations.
"""

import boto3
import os
from functools import lru_cache
from typing import Optional


# Module-level connection instances (reused across Lambda invocations)
_dynamodb_resource = None
_dynamodb_client = None
_s3_client = None
_sqs_client = None


def get_dynamodb_resource():
	"""
	Get or create a reusable DynamoDB resource.
	Reuses the connection across Lambda invocations (warm starts).

	Returns:
		boto3.resource: DynamoDB resource
	"""
	global _dynamodb_resource

	if _dynamodb_resource is None:
		region = os.environ.get('REGION', 'us-east-2')
		_dynamodb_resource = boto3.resource(
			'dynamodb',
			region_name=region,
			# Connection pool configuration
			config=boto3.session.Config(
				max_pool_connections=50,  # Increase connection pool size
				retries={
					'max_attempts': 3,
					'mode': 'adaptive'  # Adaptive retry mode
				}
			)
		)

	return _dynamodb_resource


def get_dynamodb_client():
	"""
	Get or create a reusable DynamoDB client.

	Returns:
		boto3.client: DynamoDB client
	"""
	global _dynamodb_client

	if _dynamodb_client is None:
		region = os.environ.get('REGION', 'us-east-2')
		_dynamodb_client = boto3.client(
			'dynamodb',
			region_name=region,
			config=boto3.session.Config(
				max_pool_connections=50,
				retries={
					'max_attempts': 3,
					'mode': 'adaptive'
				}
			)
		)

	return _dynamodb_client


def get_s3_client():
	"""
	Get or create a reusable S3 client.

	Returns:
		boto3.client: S3 client
	"""
	global _s3_client

	if _s3_client is None:
		_s3_client = boto3.client(
			's3',
			config=boto3.session.Config(
				max_pool_connections=50,
				retries={
					'max_attempts': 3,
					'mode': 'adaptive'
				},
				# S3-specific optimizations
				s3={
					'addressing_style': 'path'  # Use path-style addressing
				}
			)
		)

	return _s3_client


def get_sqs_client():
	"""
	Get or create a reusable SQS client.

	Returns:
		boto3.client: SQS client
	"""
	global _sqs_client

	if _sqs_client is None:
		region = os.environ.get('REGION', 'us-east-2')
		_sqs_client = boto3.client(
			'sqs',
			region_name=region,
			config=boto3.session.Config(
				max_pool_connections=50,
				retries={
					'max_attempts': 3,
					'mode': 'adaptive'
				}
			)
		)

	return _sqs_client


def get_table(table_name: str):
	"""
	Get a DynamoDB table resource with connection pooling.

	Args:
		table_name: Name of the DynamoDB table

	Returns:
		boto3.resource.Table: DynamoDB table resource
	"""
	dynamodb = get_dynamodb_resource()
	return dynamodb.Table(table_name)


# In-memory cache for frequently accessed data
_session_cache = {}
_cache_ttl = {}


def get_cached_session_data(job_id: str) -> Optional[dict]:
	"""
	Get cached session data for a job.

	Args:
		job_id: Job ID

	Returns:
		Cached session data or None
	"""
	import time

	# Check if cached and not expired
	if job_id in _session_cache:
		if job_id in _cache_ttl and time.time() < _cache_ttl[job_id]:
			return _session_cache[job_id]
		else:
			# Expired, remove from cache
			_session_cache.pop(job_id, None)
			_cache_ttl.pop(job_id, None)

	return None


def set_cached_session_data(job_id: str, session_data: dict, ttl_seconds: int = 3600):
	"""
	Cache session data for a job.

	Args:
		job_id: Job ID
		session_data: Session data to cache
		ttl_seconds: Time to live in seconds (default: 1 hour)
	"""
	import time

	_session_cache[job_id] = session_data
	_cache_ttl[job_id] = time.time() + ttl_seconds


def clear_session_cache(job_id: Optional[str] = None):
	"""
	Clear session cache for a specific job or all jobs.

	Args:
		job_id: Job ID to clear, or None to clear all
	"""
	if job_id:
		_session_cache.pop(job_id, None)
		_cache_ttl.pop(job_id, None)
	else:
		_session_cache.clear()
		_cache_ttl.clear()


# LRU cache for environment variable lookups
@lru_cache(maxsize=32)
def get_env_cached(key: str, default: Optional[str] = None) -> Optional[str]:
	"""
	Get environment variable with LRU caching.

	Args:
		key: Environment variable name
		default: Default value if not found

	Returns:
		Environment variable value
	"""
	return os.environ.get(key, default)


# Warm up connections on module import (Lambda container reuse)
def warm_up_connections():
	"""
	Pre-warm connections when Lambda container starts.
	Call this during cold start to improve first request performance.
	"""
	try:
		# Initialize connections
		get_dynamodb_resource()
		get_s3_client()
		get_sqs_client()
	except Exception:
		# Ignore errors during warm-up
		pass


# HTTP session pool for web scraping
_http_session_pool = {}


def get_http_session(job_id: str, user_agent: str = None, referrer: str = None):
	"""
	Get or create an HTTP session for a job with connection pooling.

	Args:
		job_id: Job ID
		user_agent: User agent string
		referrer: Referrer URL

	Returns:
		requests.Session: HTTP session with connection pooling
	"""
	import requests
	from requests.adapters import HTTPAdapter
	from urllib3.util.retry import Retry

	# Reuse session if exists and still valid
	if job_id in _http_session_pool:
		return _http_session_pool[job_id]

	# Create new session with connection pooling
	session = requests.Session()

	# Configure retry strategy
	retry_strategy = Retry(
		total=3,
		backoff_factor=1,
		status_forcelist=[429, 500, 502, 503, 504],
		allowed_methods=["HEAD", "GET", "OPTIONS"]
	)

	# Configure HTTP adapter with connection pooling
	adapter = HTTPAdapter(
		max_retries=retry_strategy,
		pool_connections=10,  # Number of connection pools
		pool_maxsize=20,  # Max connections per pool
		pool_block=False
	)

	session.mount("http://", adapter)
	session.mount("https://", adapter)

	# Set headers
	if user_agent:
		session.headers.update({'User-Agent': user_agent})
	if referrer:
		session.headers.update({'Referer': referrer})

	# Cache session (with reasonable limit)
	if len(_http_session_pool) < 100:  # Limit cache size
		_http_session_pool[job_id] = session

	return session


def close_http_session(job_id: str):
	"""
	Close and remove HTTP session from pool.

	Args:
		job_id: Job ID
	"""
	if job_id in _http_session_pool:
		session = _http_session_pool[job_id]
		session.close()
		del _http_session_pool[job_id]


def cleanup_http_sessions():
	"""
	Clean up all HTTP sessions in the pool.
	"""
	for session in _http_session_pool.values():
		session.close()
	_http_session_pool.clear()


# Optimize cold starts by warming up on module import
# This happens once per Lambda container lifecycle
try:
	warm_up_connections()
except Exception:
	pass  # Ignore errors during initialization

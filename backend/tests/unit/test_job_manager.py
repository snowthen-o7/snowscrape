import json
import pytest
import responses
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from moto import mock_aws


@pytest.mark.aws
class TestJobManager:
	"""Unit tests for job_manager functions."""

	@mock_aws
	def test_create_job(self, dynamodb_client, mock_env_vars):
		"""Test creating a new job."""
		from job_manager import create_job

		# Mock the parse_links_from_file function
		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com', 'http://test2.com']

			job_data = {
				'name': 'Test Job',
				'user_id': 'user-123',
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'selector': '//title/text()',
					'join': False
				}],
				'rate_limit': 5
			}

			job_id = create_job(job_data)

			assert job_id is not None
			assert isinstance(job_id, str)

			# Verify job was created in DynamoDB
			job_table = dynamodb_client.Table('SnowscrapeJobs-test')
			response = job_table.get_item(Key={'job_id': job_id})
			assert 'Item' in response
			assert response['Item']['name'] == 'Test Job'
			assert response['Item']['status'] == 'ready'
			assert response['Item']['link_count'] == 2

			# Verify URLs were created
			url_table = dynamodb_client.Table('SnowscrapeUrls-test')
			urls_response = url_table.query(
				KeyConditionExpression='job_id = :jid',
				ExpressionAttributeValues={':jid': job_id}
			)
			assert len(urls_response['Items']) == 2

	@mock_aws
	def test_create_job_with_job_id(self, dynamodb_client, mock_env_vars):
		"""Test creating a job with a pre-assigned job_id."""
		from job_manager import create_job

		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com']

			job_data = {
				'job_id': 'custom-job-id',
				'name': 'Test Job',
				'user_id': 'user-123',
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'selector': '//title/text()',
					'join': False
				}],
				'rate_limit': 5
			}

			job_id = create_job(job_data)
			assert job_id == 'custom-job-id'

	@mock_aws
	def test_delete_job(self, dynamodb_client, mock_env_vars):
		"""Test deleting a job and its URLs."""
		from job_manager import create_job, delete_job

		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com', 'http://test2.com']

			job_data = {
				'name': 'Test Job',
				'user_id': 'user-123',
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'selector': '//title/text()',
					'join': False
				}],
				'rate_limit': 5
			}

			job_id = create_job(job_data)

			# Delete the job
			result = delete_job(job_id)
			assert 'deleted successfully' in result

			# Verify job was deleted
			job_table = dynamodb_client.Table('SnowscrapeJobs-test')
			response = job_table.get_item(Key={'job_id': job_id})
			assert 'Item' not in response

			# Verify URLs were deleted
			url_table = dynamodb_client.Table('SnowscrapeUrls-test')
			urls_response = url_table.query(
				KeyConditionExpression='job_id = :jid',
				ExpressionAttributeValues={':jid': job_id}
			)
			assert len(urls_response['Items']) == 0

	@mock_aws
	def test_get_job(self, dynamodb_client, mock_env_vars):
		"""Test retrieving a specific job."""
		from job_manager import create_job, get_job

		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com']

			job_data = {
				'name': 'Test Job',
				'user_id': 'user-123',
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'selector': '//title/text()',
					'join': False
				}],
				'rate_limit': 5
			}

			job_id = create_job(job_data)

			# Retrieve the job
			job = get_job(job_id)
			assert job is not None
			assert job['job_id'] == job_id
			assert job['name'] == 'Test Job'
			assert job['status'] == 'ready'

	@mock_aws
	def test_get_job_nonexistent(self, dynamodb_client, mock_env_vars):
		"""Test retrieving a non-existent job returns None."""
		from job_manager import get_job

		job = get_job('nonexistent-job-id')
		assert job is None

	@mock_aws
	def test_get_all_jobs(self, dynamodb_client, mock_env_vars):
		"""Test retrieving all jobs."""
		from job_manager import create_job, get_all_jobs

		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com']

			# Create multiple jobs
			for i in range(3):
				job_data = {
					'name': f'Test Job {i}',
					'user_id': 'user-123',
					'source': 'http://example.com/urls.csv',
					'file_mapping': {
						'delimiter': ',',
						'enclosure': '"',
						'escape': '\\',
						'url_column': 0
					},
					'queries': [{
						'name': 'title',
						'type': 'xpath',
						'selector': '//title/text()',
						'join': False
					}],
					'rate_limit': 5
				}
				create_job(job_data)

			# Retrieve all jobs
			result = get_all_jobs()
			assert isinstance(result, dict)
			assert 'items' in result
			assert len(result['items']) == 3

	@mock_aws
	def test_pause_job(self, dynamodb_client, mock_env_vars):
		"""Test pausing a job."""
		from job_manager import create_job, pause_job, get_job

		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com']

			job_data = {
				'name': 'Test Job',
				'user_id': 'user-123',
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'selector': '//title/text()',
					'join': False
				}],
				'rate_limit': 5
			}

			job_id = create_job(job_data)

			# Pause the job
			result = pause_job(job_id)
			assert 'paused successfully' in result

			# Verify status changed
			job = get_job(job_id)
			assert job['status'] == 'paused'

	@mock_aws
	def test_cancel_job(self, dynamodb_client, mock_env_vars):
		"""Test cancelling a job."""
		from job_manager import create_job, cancel_job, get_job

		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com']

			job_data = {
				'name': 'Test Job',
				'user_id': 'user-123',
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'selector': '//title/text()',
					'join': False
				}],
				'rate_limit': 5
			}

			job_id = create_job(job_data)

			# Cancel the job
			result = cancel_job(job_id)
			assert 'cancelled successfully' in result

			# Verify status changed and cancelled_at is set
			job = get_job(job_id)
			assert job['status'] == 'cancelled'
			assert 'cancelled_at' in job

	@mock_aws
	def test_resume_job(self, dynamodb_client, mock_env_vars):
		"""Test resuming a paused job."""
		from job_manager import create_job, pause_job, resume_job, get_job

		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com']

			job_data = {
				'name': 'Test Job',
				'user_id': 'user-123',
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'selector': '//title/text()',
					'join': False
				}],
				'rate_limit': 5
			}

			job_id = create_job(job_data)
			pause_job(job_id)

			# Resume the job
			result = resume_job(job_id)
			assert 'resumed successfully' in result

			# Verify status changed
			job = get_job(job_id)
			assert job['status'] == 'active'

	@mock_aws
	def test_update_job(self, dynamodb_client, mock_env_vars):
		"""Test updating job information."""
		from job_manager import create_job, update_job, get_job

		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com']

			job_data = {
				'name': 'Test Job',
				'user_id': 'user-123',
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'selector': '//title/text()',
					'join': False
				}],
				'rate_limit': 5
			}

			job_id = create_job(job_data)

			# Update the job
			updated_data = {
				'name': 'Updated Job Name',
				'rate_limit': 3,
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'query': '//title/text()'
				}]
			}

			result = update_job(job_id, updated_data)
			assert 'updated successfully' in result

			# Verify changes
			job = get_job(job_id)
			assert job['name'] == 'Updated Job Name'
			assert job['rate_limit'] == 3

	@mock_aws
	def test_update_job_invalid_data(self, dynamodb_client, mock_env_vars):
		"""Test updating job with invalid data."""
		from job_manager import create_job, update_job

		with patch('utils.parse_links_from_file') as mock_parse:
			mock_parse.return_value = ['http://test1.com']

			job_data = {
				'name': 'Test Job',
				'user_id': 'user-123',
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'selector': '//title/text()',
					'join': False
				}],
				'rate_limit': 5
			}

			job_id = create_job(job_data)

			# Try to update with invalid data
			invalid_data = {
				'name': 'Updated Job',
				'rate_limit': 99,  # Invalid: should be 1-8
				'source': 'http://example.com/urls.csv',
				'file_mapping': {
					'delimiter': ',',
					'enclosure': '"',
					'escape': '\\',
					'url_column': 0
				},
				'queries': [{
					'name': 'title',
					'type': 'xpath',
					'query': '//title/text()'
				}]
			}

			result = update_job(job_id, invalid_data)
			assert result is None  # Should return None on validation error

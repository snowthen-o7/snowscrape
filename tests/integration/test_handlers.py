import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from moto import mock_aws


@pytest.mark.integration
@pytest.mark.aws
class TestHandlers:
	"""Integration tests for Lambda handler functions."""

	@mock_aws
	def test_create_job_handler_success(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test successful job creation via handler."""
		from handler import create_job_handler

		with patch('handler.parse_links_from_file') as mock_parse:
			with patch('handler.validate_clerk_token') as mock_validate:
				mock_parse.return_value = ['http://test1.com', 'http://test2.com']
				mock_validate.return_value = {'sub': 'user-123'}

				event = {
					'headers': {
						'Authorization': 'Bearer test-token'
					},
					'body': json.dumps({
						'name': 'Test Job',
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
						}],
						'rate_limit': 5
					})
				}

				response = create_job_handler(event, lambda_context)

				assert response['statusCode'] == 201
				body = json.loads(response['body'])
				assert 'job_id' in body
				assert body['message'] == 'Job created successfully'

	@mock_aws
	def test_create_job_handler_no_token(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test job creation without authentication token."""
		from handler import create_job_handler

		event = {
			'headers': {},
			'body': json.dumps({
				'name': 'Test Job',
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
				}],
				'rate_limit': 5
			})
		}

		response = create_job_handler(event, lambda_context)

		assert response['statusCode'] == 401
		body = json.loads(response['body'])
		assert 'Unauthorized' in body['message']

	@mock_aws
	def test_create_job_handler_invalid_token(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test job creation with invalid authentication token."""
		from handler import create_job_handler

		with patch('handler.validate_clerk_token') as mock_validate:
			mock_validate.side_effect = Exception('Invalid token.')

			event = {
				'headers': {
					'Authorization': 'Bearer invalid-token'
				},
				'body': json.dumps({
					'name': 'Test Job',
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
					}],
					'rate_limit': 5
				})
			}

			response = create_job_handler(event, lambda_context)

			assert response['statusCode'] == 401

	@mock_aws
	def test_delete_job_handler_success(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test successful job deletion via handler."""
		from handler import create_job_handler, delete_job_handler

		# First create a job
		with patch('handler.parse_links_from_file') as mock_parse:
			with patch('handler.validate_clerk_token') as mock_validate:
				mock_parse.return_value = ['http://test1.com']
				mock_validate.return_value = {'sub': 'user-123'}

				create_event = {
					'headers': {'Authorization': 'Bearer test-token'},
					'body': json.dumps({
						'name': 'Test Job',
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
						}],
						'rate_limit': 5
					})
				}

				create_response = create_job_handler(create_event, lambda_context)
				job_id = json.loads(create_response['body'])['job_id']

				# Now delete it
				with patch('handler.validate_clerk_token') as mock_validate_delete:
					mock_validate_delete.return_value = 'user-123'

					delete_event = {
						'headers': {'Authorization': 'Bearer test-token'},
						'pathParameters': {'job_id': job_id}
					}

					response = delete_job_handler(delete_event, lambda_context)

					assert response['statusCode'] == 200
					body = json.loads(response['body'])
					assert body['message'] == 'Job deleted successfully'

	@mock_aws
	def test_delete_job_handler_no_auth(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test job deletion without authentication."""
		from handler import delete_job_handler

		event = {
			'headers': {},
			'pathParameters': {'job_id': 'test-job-123'}
		}

		response = delete_job_handler(event, lambda_context)

		assert response['statusCode'] == 401
		body = json.loads(response['body'])
		assert 'Unauthorized' in body['message']

	@mock_aws
	def test_get_job_details_handler_success(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test retrieving job details via handler."""
		from handler import create_job_handler, get_job_details_handler

		# First create a job
		with patch('handler.parse_links_from_file') as mock_parse:
			with patch('handler.validate_clerk_token') as mock_validate:
				mock_parse.return_value = ['http://test1.com']
				mock_validate.return_value = {'sub': 'user-123'}

				create_event = {
					'headers': {'Authorization': 'Bearer test-token'},
					'body': json.dumps({
						'name': 'Test Job',
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
						}],
						'rate_limit': 5
					})
				}

				create_response = create_job_handler(create_event, lambda_context)
				job_id = json.loads(create_response['body'])['job_id']

				# Now retrieve it
				get_event = {
					'pathParameters': {'job_id': job_id}
				}

				response = get_job_details_handler(get_event, lambda_context)

				assert response['statusCode'] == 200
				body = json.loads(response['body'])
				assert body['job_id'] == job_id
				assert body['name'] == 'Test Job'

	@mock_aws
	def test_get_job_details_handler_not_found(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test retrieving non-existent job details."""
		from handler import get_job_details_handler

		event = {
			'pathParameters': {'job_id': 'nonexistent-job-id'}
		}

		response = get_job_details_handler(event, lambda_context)

		assert response['statusCode'] == 404
		body = json.loads(response['body'])
		assert body['message'] == 'Job not found'

	@mock_aws
	def test_pause_job_handler_success(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test pausing a job via handler."""
		from handler import create_job_handler, pause_job_handler

		# First create a job
		with patch('handler.parse_links_from_file') as mock_parse:
			with patch('handler.validate_clerk_token') as mock_validate:
				mock_parse.return_value = ['http://test1.com']
				mock_validate.return_value = {'sub': 'user-123'}

				create_event = {
					'headers': {'Authorization': 'Bearer test-token'},
					'body': json.dumps({
						'name': 'Test Job',
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
						}],
						'rate_limit': 5
					})
				}

				create_response = create_job_handler(create_event, lambda_context)
				job_id = json.loads(create_response['body'])['job_id']

				# Now pause it
				with patch('handler.validate_clerk_token') as mock_validate_pause:
					mock_validate_pause.return_value = 'user-123'

					pause_event = {
						'headers': {'Authorization': 'Bearer test-token'},
						'pathParameters': {'job_id': job_id}
					}

					response = pause_job_handler(pause_event, lambda_context)

					assert response['statusCode'] == 200
					body = json.loads(response['body'])
					assert body['message'] == 'Job paused successfully'

	@mock_aws
	def test_cancel_job_handler_success(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test cancelling a job via handler."""
		from handler import create_job_handler, cancel_job_handler

		# First create a job
		with patch('handler.parse_links_from_file') as mock_parse:
			with patch('handler.validate_clerk_token') as mock_validate:
				mock_parse.return_value = ['http://test1.com']
				mock_validate.return_value = {'sub': 'user-123'}

				create_event = {
					'headers': {'Authorization': 'Bearer test-token'},
					'body': json.dumps({
						'name': 'Test Job',
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
						}],
						'rate_limit': 5
					})
				}

				create_response = create_job_handler(create_event, lambda_context)
				job_id = json.loads(create_response['body'])['job_id']

				# Now cancel it
				with patch('handler.validate_clerk_token') as mock_validate_cancel:
					mock_validate_cancel.return_value = 'user-123'

					cancel_event = {
						'headers': {'Authorization': 'Bearer test-token'},
						'pathParameters': {'job_id': job_id}
					}

					response = cancel_job_handler(cancel_event, lambda_context)

					assert response['statusCode'] == 200
					body = json.loads(response['body'])
					assert body['message'] == 'Job cancelled successfully'

	@mock_aws
	def test_get_all_job_statuses_handler(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test retrieving all job statuses via handler."""
		from handler import create_job_handler, get_all_job_statuses_handler

		# Create multiple jobs
		with patch('handler.parse_links_from_file') as mock_parse:
			with patch('handler.validate_clerk_token') as mock_validate:
				mock_parse.return_value = ['http://test1.com']
				mock_validate.return_value = {'sub': 'user-123'}

				for i in range(3):
					create_event = {
						'headers': {'Authorization': 'Bearer test-token'},
						'body': json.dumps({
							'name': f'Test Job {i}',
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
							}],
							'rate_limit': 5
						})
					}
					create_job_handler(create_event, lambda_context)

				# Now retrieve all jobs
				event = {}
				response = get_all_job_statuses_handler(event, lambda_context)

				assert response['statusCode'] == 200
				jobs = json.loads(response['body'])
				assert isinstance(jobs, list)
				assert len(jobs) == 3

	@mock_aws
	def test_update_job_handler_success(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test updating a job via handler."""
		from handler import create_job_handler, update_job_handler

		# First create a job
		with patch('handler.parse_links_from_file') as mock_parse:
			with patch('handler.validate_clerk_token') as mock_validate:
				mock_parse.return_value = ['http://test1.com']
				mock_validate.return_value = {'sub': 'user-123'}

				create_event = {
					'headers': {'Authorization': 'Bearer test-token'},
					'body': json.dumps({
						'name': 'Test Job',
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
						}],
						'rate_limit': 5
					})
				}

				create_response = create_job_handler(create_event, lambda_context)
				job_id = json.loads(create_response['body'])['job_id']

				# Now update it
				with patch('handler.validate_clerk_token') as mock_validate_update:
					mock_validate_update.return_value = 'user-123'

					update_event = {
						'headers': {'Authorization': 'Bearer test-token'},
						'pathParameters': {'job_id': job_id},
						'body': json.dumps({
							'name': 'Updated Job Name',
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
							}],
							'rate_limit': 3
						})
					}

					response = update_job_handler(update_event, lambda_context)

					assert response['statusCode'] == 200
					body = json.loads(response['body'])
					assert body['message'] == 'Job updated successfully'

	@mock_aws
	def test_update_job_handler_no_auth(self, dynamodb_client, mock_env_vars, lambda_context):
		"""Test job update without authentication."""
		from handler import update_job_handler

		event = {
			'headers': {},
			'pathParameters': {'job_id': 'test-job-123'},
			'body': json.dumps({
				'name': 'Updated Job',
				'rate_limit': 5
			})
		}

		response = update_job_handler(event, lambda_context)

		assert response['statusCode'] == 401
		body = json.loads(response['body'])
		assert 'Unauthorized' in body['message']

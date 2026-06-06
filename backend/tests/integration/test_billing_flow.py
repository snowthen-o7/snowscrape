"""Integration tests covering full billing-driven user flows."""
import json
import pytest
from unittest.mock import patch


@pytest.mark.integration
@pytest.mark.aws
class TestLockedUserAccess:
	def test_locked_user_cannot_create_job(
		self, dynamodb_client, mock_env_vars, lambda_context
	):
		from handler import create_job_handler
		event = {
			"headers": {"Authorization": "Bearer t"},
			"body": json.dumps({
				"name": "Test",
				"source": "https://example.com/u.csv",
				"file_mapping": {"delimiter": ",", "enclosure": '"', "escape": "\\", "url_column": 0},
				"queries": [{"name": "title", "type": "xpath", "query": "//title"}],
				"rate_limit": 5,
			}),
		}
		with patch("handler.resolve_user_id", return_value="user-locked"):
			resp = create_job_handler(event, lambda_context)
		assert resp["statusCode"] == 402
		body = json.loads(resp["body"])
		assert body["plan"] == "locked"

	def test_locked_user_can_list_jobs(
		self, dynamodb_client, mock_env_vars, lambda_context
	):
		from handler import get_all_job_statuses_handler
		event = {"headers": {"Authorization": "Bearer t"}}
		with patch("handler.resolve_user_id", return_value="user-locked"):
			resp = get_all_job_statuses_handler(event, lambda_context)
		# 200 with empty list — read access preserved for locked users
		assert resp["statusCode"] == 200

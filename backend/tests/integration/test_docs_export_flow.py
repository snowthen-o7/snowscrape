"""Integration test for SQS-triggered Docs export Lambda."""
import json
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def env(monkeypatch):
	monkeypatch.setenv("DYNAMODB_EXPORT_DESTINATIONS_TABLE", "ExportDestinations-test")
	monkeypatch.setenv("DYNAMODB_GOOGLE_ACCOUNTS_TABLE", "GoogleAccounts-test")
	monkeypatch.setenv("DYNAMODB_DOCS_EXPORTS_TABLE", "DocsExports-test")
	monkeypatch.setenv("S3_BUCKET", "results-test")
	monkeypatch.setenv("OAUTH_TOKEN_KMS_KEY_ID", "test-key-id")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-abc")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret-xyz")
	monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3001/cb")


@pytest.fixture
def aws_resources(env):
	with mock_aws():
		dynamo = boto3.resource("dynamodb")
		for name, fields in [
			("ExportDestinations-test", [("destination_id", "S")]),
			("GoogleAccounts-test", [("user_id", "S")]),
			("DocsExports-test", [("export_id", "S")]),
		]:
			dynamo.create_table(
				TableName=name,
				KeySchema=[{"AttributeName": fields[0][0], "KeyType": "HASH"}],
				AttributeDefinitions=[{"AttributeName": f[0], "AttributeType": f[1]} for f in fields],
				BillingMode="PAY_PER_REQUEST",
			)
		s3 = boto3.client("s3")
		s3.create_bucket(
			Bucket="results-test",
			CreateBucketConfiguration={"LocationConstraint": "us-east-2"},
		)
		s3.put_object(
			Bucket="results-test",
			Key="results/job-1.json",
			Body=json.dumps([
				{"url": "https://a/1", "title": "Post 1", "body": "Hello"},
				{"url": "https://a/2", "title": "Post 2", "body": "World"},
			]).encode("utf-8"),
		)
		dynamo.Table("ExportDestinations-test").put_item(Item={
			"destination_id": "d-1", "user_id": "user_abc", "name": "Mine",
			"type": "google_docs", "drive_folder_id": "folder-xyz",
			"naming_template": "{{job_name}} — {{date}}",
			"mode": "new_doc_per_run", "format_template": "structured_log",
			"google_user_id": "g-123",
		})
		dynamo.Table("GoogleAccounts-test").put_item(Item={
			"user_id": "user_abc", "google_user_id": "g-123",
			"email": "u@example.com", "refresh_token_ciphertext": "ciphertext",
		})
		yield {"dynamo": dynamo, "s3": s3}


@patch("docs_export_handler.decrypt_refresh_token", return_value="refresh-token-plain")
@patch("docs_export_handler._build_drive_service")
@patch("docs_export_handler._build_docs_service")
@patch("docs_export_handler.refresh_access_token")
def test_export_creates_doc_and_logs(
	mock_refresh, mock_docs, mock_drive, _mock_decrypt, aws_resources,
):
	mock_refresh.return_value = {"access_token": "access-fresh", "expiry": "2026-06-01T13:00:00"}
	mock_drive.return_value.files.return_value.create.return_value.execute.return_value = {
		"id": "doc-id-123", "webViewLink": "https://docs.google.com/document/d/doc-id-123",
	}
	mock_docs.return_value.documents.return_value.batchUpdate.return_value.execute.return_value = {}

	from docs_export_handler import docs_export_handler

	sqs_event = {"Records": [{
		"messageId": "msg-1",
		"body": json.dumps({
			"export_id": "exp-1",
			"destination_id": "d-1",
			"job_id": "job-1",
			"user_id": "user_abc",
			"results_s3_key": "results/job-1.json",
			"job_name": "Test Job",
		}),
	}]}

	result = docs_export_handler(sqs_event, None)

	assert result.get("batchItemFailures", []) == []
	mock_drive.return_value.files.return_value.create.assert_called_once()
	create_kwargs = mock_drive.return_value.files.return_value.create.call_args.kwargs
	assert create_kwargs["body"]["parents"] == ["folder-xyz"]
	assert "Test Job" in create_kwargs["body"]["name"]
	mock_docs.return_value.documents.return_value.batchUpdate.assert_called_once()

	log = aws_resources["dynamo"].Table("DocsExports-test").get_item(Key={"export_id": "exp-1"})["Item"]
	assert log["status"] == "success"
	assert log["doc_id"] == "doc-id-123"
	assert log["doc_url"] == "https://docs.google.com/document/d/doc-id-123"


@patch("docs_export_handler.decrypt_refresh_token", return_value="refresh-token-plain")
@patch("docs_export_handler._build_drive_service")
@patch("docs_export_handler._build_docs_service")
@patch("docs_export_handler.refresh_access_token")
def test_export_returns_failure_on_api_error(
	mock_refresh, mock_docs, mock_drive, _mock_decrypt, aws_resources,
):
	mock_refresh.return_value = {"access_token": "at", "expiry": None}
	mock_drive.return_value.files.return_value.create.return_value.execute.side_effect = RuntimeError("api boom")

	from docs_export_handler import docs_export_handler

	sqs_event = {"Records": [{
		"messageId": "msg-1",
		"body": json.dumps({
			"export_id": "exp-1",
			"destination_id": "d-1",
			"job_id": "job-1",
			"user_id": "user_abc",
			"results_s3_key": "results/job-1.json",
			"job_name": "Test Job",
		}),
	}]}

	result = docs_export_handler(sqs_event, None)

	assert result["batchItemFailures"] == [{"itemIdentifier": "msg-1"}]
	log = aws_resources["dynamo"].Table("DocsExports-test").get_item(Key={"export_id": "exp-1"})["Item"]
	assert log["status"] == "failed"
	assert "api boom" in log["error"]

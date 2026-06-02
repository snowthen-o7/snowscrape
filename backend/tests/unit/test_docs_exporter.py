"""Unit tests for DocsExporter."""
import json
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def env(monkeypatch):
	monkeypatch.setenv("DYNAMODB_EXPORT_DESTINATIONS_TABLE", "ExportDestinations-test")
	monkeypatch.setenv("SQS_DOCS_EXPORT_QUEUE_URL", "https://sqs.test/queue")


@pytest.fixture
def aws_setup(env):
	with mock_aws():
		dynamo = boto3.resource("dynamodb")
		dynamo.create_table(
			TableName="ExportDestinations-test",
			KeySchema=[{"AttributeName": "destination_id", "KeyType": "HASH"}],
			AttributeDefinitions=[{"AttributeName": "destination_id", "AttributeType": "S"}],
			BillingMode="PAY_PER_REQUEST",
		)
		sqs = boto3.client("sqs")
		queue_url = sqs.create_queue(QueueName="docs-export-test")["QueueUrl"]
		yield {"dynamo": dynamo, "sqs": sqs, "queue_url": queue_url}


def test_dispatch_skips_when_no_destinations(aws_setup, monkeypatch):
	monkeypatch.setenv("SQS_DOCS_EXPORT_QUEUE_URL", aws_setup["queue_url"])
	from docs_exporter import DocsExporter

	count = DocsExporter.dispatch_job_completed(
		job_id="job-1",
		user_id="user_abc",
		destination_ids=[],
		results_s3_key="results/job-1.json",
		job_data={"name": "Test"},
	)
	assert count == 0


def test_dispatch_sends_one_message_per_destination(aws_setup, monkeypatch):
	monkeypatch.setenv("SQS_DOCS_EXPORT_QUEUE_URL", aws_setup["queue_url"])
	dynamo = aws_setup["dynamo"]
	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-1", "user_id": "user_abc", "name": "A",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
		"google_user_id": "g-123",
	})
	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-2", "user_id": "user_abc", "name": "B",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "compact_list",
		"google_user_id": "g-123",
	})

	from docs_exporter import DocsExporter

	count = DocsExporter.dispatch_job_completed(
		job_id="job-1",
		user_id="user_abc",
		destination_ids=["d-1", "d-2"],
		results_s3_key="results/job-1.json",
		job_data={"name": "Test"},
	)

	assert count == 2
	messages = aws_setup["sqs"].receive_message(
		QueueUrl=aws_setup["queue_url"],
		MaxNumberOfMessages=10,
	).get("Messages", [])
	assert len(messages) == 2
	parsed = [json.loads(m["Body"]) for m in messages]
	dest_ids = sorted(m["destination_id"] for m in parsed)
	assert dest_ids == ["d-1", "d-2"]
	for m in parsed:
		assert m["job_id"] == "job-1"
		assert m["user_id"] == "user_abc"
		assert m["results_s3_key"] == "results/job-1.json"
		assert "export_id" in m


def test_dispatch_ignores_missing_destination_ids(aws_setup, monkeypatch):
	monkeypatch.setenv("SQS_DOCS_EXPORT_QUEUE_URL", aws_setup["queue_url"])
	from docs_exporter import DocsExporter

	count = DocsExporter.dispatch_job_completed(
		job_id="job-1",
		user_id="user_abc",
		destination_ids=["missing-d"],
		results_s3_key="results/job-1.json",
		job_data={"name": "Test"},
	)
	assert count == 0

"""Unit tests for export_destination_handler."""
import json
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def env(monkeypatch):
	monkeypatch.setenv("DYNAMODB_EXPORT_DESTINATIONS_TABLE", "ExportDestinations-test")
	monkeypatch.setenv("DYNAMODB_GOOGLE_ACCOUNTS_TABLE", "GoogleAccounts-test")
	monkeypatch.setenv("CORS_ALLOWED_ORIGIN", "http://localhost:3001")


@pytest.fixture
def dynamo(env):
	with mock_aws():
		client = boto3.resource("dynamodb")
		client.create_table(
			TableName="ExportDestinations-test",
			KeySchema=[{"AttributeName": "destination_id", "KeyType": "HASH"}],
			AttributeDefinitions=[
				{"AttributeName": "destination_id", "AttributeType": "S"},
				{"AttributeName": "user_id", "AttributeType": "S"},
			],
			GlobalSecondaryIndexes=[{
				"IndexName": "UserIdIndex",
				"KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
				"Projection": {"ProjectionType": "ALL"},
			}],
			BillingMode="PAY_PER_REQUEST",
		)
		client.create_table(
			TableName="GoogleAccounts-test",
			KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
			AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
			BillingMode="PAY_PER_REQUEST",
		)
		client.Table("GoogleAccounts-test").put_item(Item={
			"user_id": "user_abc",
			"google_user_id": "g-123",
			"email": "u@example.com",
			"refresh_token_ciphertext": "x",
		})
		yield client


def _auth_event(body=None, path_params=None):
	return {
		"headers": {"Authorization": "Bearer t", "origin": "http://localhost:3001"},
		"body": json.dumps(body) if body is not None else None,
		"pathParameters": path_params or {},
	}


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_create_destination_persists(_clerk, dynamo, lambda_context):
	from export_destination_handler import create_destination_handler

	resp = create_destination_handler(_auth_event({
		"name": "My LinkedIn export",
		"type": "google_docs",
		"drive_folder_id": "folder-xyz",
		"naming_template": "{{job_name}} — {{date}}",
		"mode": "new_doc_per_run",
		"format_template": "structured_log",
	}), lambda_context)

	assert resp["statusCode"] == 201
	body = json.loads(resp["body"])
	assert body["name"] == "My LinkedIn export"
	assert "destination_id" in body

	items = dynamo.Table("ExportDestinations-test").scan()["Items"]
	assert len(items) == 1
	assert items[0]["user_id"] == "user_abc"
	assert items[0]["drive_folder_id"] == "folder-xyz"


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_create_destination_rejects_without_google_account(_clerk, dynamo, lambda_context):
	from export_destination_handler import create_destination_handler

	dynamo.Table("GoogleAccounts-test").delete_item(Key={"user_id": "user_abc"})

	resp = create_destination_handler(_auth_event({
		"name": "x",
		"type": "google_docs",
		"drive_folder_id": "f",
		"naming_template": "{{date}}",
		"mode": "new_doc_per_run",
		"format_template": "structured_log",
	}), lambda_context)

	assert resp["statusCode"] == 400
	assert "google account" in json.loads(resp["body"])["message"].lower()


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_list_returns_only_users_destinations(_clerk, dynamo, lambda_context):
	from export_destination_handler import list_destinations_handler

	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-1", "user_id": "user_abc", "name": "Mine",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
	})
	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-2", "user_id": "other_user", "name": "Theirs",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
	})

	resp = list_destinations_handler(_auth_event(), lambda_context)

	body = json.loads(resp["body"])
	assert len(body["destinations"]) == 1
	assert body["destinations"][0]["name"] == "Mine"


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_delete_destination(_clerk, dynamo, lambda_context):
	from export_destination_handler import delete_destination_handler

	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-1", "user_id": "user_abc", "name": "Mine",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
	})

	resp = delete_destination_handler(
		_auth_event(path_params={"destination_id": "d-1"}),
		lambda_context,
	)

	assert resp["statusCode"] == 204
	assert "Item" not in dynamo.Table("ExportDestinations-test").get_item(Key={"destination_id": "d-1"})


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_delete_other_users_destination_forbidden(_clerk, dynamo, lambda_context):
	from export_destination_handler import delete_destination_handler

	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-1", "user_id": "other_user", "name": "Theirs",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
	})

	resp = delete_destination_handler(
		_auth_event(path_params={"destination_id": "d-1"}),
		lambda_context,
	)

	assert resp["statusCode"] == 404
	assert "Item" in dynamo.Table("ExportDestinations-test").get_item(Key={"destination_id": "d-1"})

"""Unit tests for google_account_handler."""
import json
import os
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def env(monkeypatch):
	monkeypatch.setenv("DYNAMODB_GOOGLE_ACCOUNTS_TABLE", "GoogleAccounts-test")
	monkeypatch.setenv("CORS_ALLOWED_ORIGIN", "http://localhost:3001")
	monkeypatch.setenv("OAUTH_TOKEN_KMS_KEY_ID", "test-key-id")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-abc")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret-xyz")
	monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3001/cb")


@pytest.fixture
def dynamo(env):
	with mock_aws():
		client = boto3.resource("dynamodb")
		client.create_table(
			TableName="GoogleAccounts-test",
			KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
			AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
			BillingMode="PAY_PER_REQUEST",
		)
		yield client


def _auth_event(body=None):
	return {
		"headers": {"Authorization": "Bearer token-x", "origin": "http://localhost:3001"},
		"body": json.dumps(body) if body is not None else None,
	}


@patch("google_account_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_get_auth_url_returns_consent_url(_mock_clerk, dynamo, lambda_context):
	from google_account_handler import get_auth_url_handler

	resp = get_auth_url_handler(_auth_event(), lambda_context)

	assert resp["statusCode"] == 200
	body = json.loads(resp["body"])
	assert body["auth_url"].startswith("https://accounts.google.com")
	assert "state" in body


@patch("google_account_handler.fetch_google_user_info")
@patch("google_account_handler.exchange_code_for_credentials")
@patch("google_account_handler.encrypt_refresh_token", return_value="ciphertext")
@patch("google_account_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_callback_persists_account(_clerk, _enc, mock_exchange, mock_userinfo, dynamo, lambda_context):
	from google_account_handler import oauth_callback_handler

	mock_exchange.return_value = {
		"access_token": "at",
		"refresh_token": "rt",
		"expiry": "2026-06-01T12:00:00",
		"scopes": ["https://www.googleapis.com/auth/drive.file"],
	}
	mock_userinfo.return_value = {
		"google_user_id": "g-123",
		"email": "u@example.com",
		"name": "U",
	}
	event = _auth_event({"code": "auth-code-x", "state": "state-x"})

	resp = oauth_callback_handler(event, lambda_context)

	assert resp["statusCode"] == 200
	item = dynamo.Table("GoogleAccounts-test").get_item(Key={"user_id": "user_abc"})["Item"]
	assert item["google_user_id"] == "g-123"
	assert item["email"] == "u@example.com"
	assert item["refresh_token_ciphertext"] == "ciphertext"


@patch("google_account_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_list_returns_connected_account(_clerk, dynamo, lambda_context):
	from google_account_handler import list_google_accounts_handler

	dynamo.Table("GoogleAccounts-test").put_item(Item={
		"user_id": "user_abc",
		"google_user_id": "g-123",
		"email": "u@example.com",
		"name": "U",
		"connected_at": "2026-06-01T00:00:00",
		"refresh_token_ciphertext": "ciphertext",
	})

	resp = list_google_accounts_handler(_auth_event(), lambda_context)

	assert resp["statusCode"] == 200
	body = json.loads(resp["body"])
	assert len(body["accounts"]) == 1
	assert body["accounts"][0]["email"] == "u@example.com"
	assert "refresh_token_ciphertext" not in body["accounts"][0]


@patch("google_account_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_revoke_deletes_account(_clerk, dynamo, lambda_context):
	from google_account_handler import revoke_google_account_handler

	dynamo.Table("GoogleAccounts-test").put_item(Item={
		"user_id": "user_abc",
		"google_user_id": "g-123",
		"email": "u@example.com",
		"refresh_token_ciphertext": "ciphertext",
	})

	resp = revoke_google_account_handler(_auth_event(), lambda_context)

	assert resp["statusCode"] == 204
	assert "Item" not in dynamo.Table("GoogleAccounts-test").get_item(Key={"user_id": "user_abc"})

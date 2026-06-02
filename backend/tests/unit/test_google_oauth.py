"""Unit tests for google_oauth module."""
import os
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch):
	monkeypatch.setenv("OAUTH_TOKEN_KMS_KEY_ID", "test-key-id")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-abc")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret-xyz")
	monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3001/cb")


def test_encrypt_token_calls_kms_with_key_id(monkeypatch):
	from google_oauth import encrypt_refresh_token

	fake_kms = MagicMock()
	fake_kms.encrypt.return_value = {"CiphertextBlob": b"ciphertext-bytes"}
	monkeypatch.setattr("google_oauth._kms_client", lambda: fake_kms)

	result = encrypt_refresh_token("plaintext-token")

	fake_kms.encrypt.assert_called_once()
	kwargs = fake_kms.encrypt.call_args.kwargs
	assert kwargs["KeyId"] == "test-key-id"
	assert kwargs["Plaintext"] == b"plaintext-token"
	assert result == "Y2lwaGVydGV4dC1ieXRlcw=="  # base64 of "ciphertext-bytes"


def test_decrypt_token_returns_plaintext(monkeypatch):
	from google_oauth import decrypt_refresh_token

	fake_kms = MagicMock()
	fake_kms.decrypt.return_value = {"Plaintext": b"plaintext-token"}
	monkeypatch.setattr("google_oauth._kms_client", lambda: fake_kms)

	result = decrypt_refresh_token("Y2lwaGVydGV4dC1ieXRlcw==")

	assert result == "plaintext-token"
	fake_kms.decrypt.assert_called_once()
	assert fake_kms.decrypt.call_args.kwargs["CiphertextBlob"] == b"ciphertext-bytes"


def test_build_consent_url_includes_state_and_scopes():
	from google_oauth import build_consent_url

	url, state = build_consent_url(user_id="user_123")

	assert "accounts.google.com" in url
	assert "client_id=client-abc" in url
	assert "redirect_uri=http%3A%2F%2Flocalhost%3A3001%2Fcb" in url
	assert "scope=" in url
	assert "access_type=offline" in url
	assert "prompt=consent" in url
	assert state in url
	assert len(state) >= 32


def test_exchange_code_returns_credentials(monkeypatch):
	from google_oauth import exchange_code_for_credentials

	fake_creds = MagicMock(
		token="access-token",
		refresh_token="refresh-token",
		expiry=None,
		scopes=["https://www.googleapis.com/auth/drive.file"],
	)
	fake_flow = MagicMock()
	fake_flow.credentials = fake_creds
	monkeypatch.setattr("google_oauth._build_flow", lambda: fake_flow)

	result = exchange_code_for_credentials(code="auth-code-123")

	fake_flow.fetch_token.assert_called_once_with(code="auth-code-123")
	assert result["access_token"] == "access-token"
	assert result["refresh_token"] == "refresh-token"
	assert "drive.file" in result["scopes"][0]


def test_refresh_access_token_calls_google(monkeypatch):
	from google_oauth import refresh_access_token

	fake_creds = MagicMock()
	fake_creds.token = "new-access-token"
	fake_creds.expiry = MagicMock()
	fake_creds.expiry.isoformat.return_value = "2026-06-01T12:00:00"

	monkeypatch.setattr(
		"google_oauth.Credentials",
		MagicMock(return_value=fake_creds),
	)
	monkeypatch.setattr("google_oauth.Request", MagicMock())

	result = refresh_access_token(refresh_token="refresh-abc")

	fake_creds.refresh.assert_called_once()
	assert result["access_token"] == "new-access-token"
	assert result["expiry"] == "2026-06-01T12:00:00"


def test_fetch_google_user_info(monkeypatch):
	from google_oauth import fetch_google_user_info

	fake_response = MagicMock()
	fake_response.json.return_value = {
		"sub": "google-user-123",
		"email": "user@example.com",
		"name": "Test User",
	}
	fake_response.raise_for_status.return_value = None

	fake_requests_get = MagicMock(return_value=fake_response)
	monkeypatch.setattr("google_oauth.requests.get", fake_requests_get)

	result = fetch_google_user_info(access_token="access-abc")

	assert result["google_user_id"] == "google-user-123"
	assert result["email"] == "user@example.com"
	assert result["name"] == "Test User"
	called_url = fake_requests_get.call_args.args[0]
	assert "userinfo" in called_url
	headers = fake_requests_get.call_args.kwargs["headers"]
	assert headers["Authorization"] == "Bearer access-abc"

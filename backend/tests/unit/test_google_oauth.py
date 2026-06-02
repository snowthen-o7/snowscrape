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

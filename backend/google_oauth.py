"""
Google OAuth flow helpers.
Handles consent URL generation, code-for-token exchange, token refresh,
and KMS encryption/decryption of refresh tokens.
"""
import base64
import os
import secrets
from typing import Dict, Optional

import boto3
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from logger import get_logger

logger = get_logger(__name__)

OAUTH_SCOPES = [
	"https://www.googleapis.com/auth/drive.file",
	"https://www.googleapis.com/auth/drive.metadata.readonly",
	"https://www.googleapis.com/auth/documents",
	"openid",
	"email",
	"profile",
]


def _kms_client():
	return boto3.client("kms")


def encrypt_refresh_token(plaintext: str) -> str:
	"""Encrypt with KMS; return base64-encoded ciphertext."""
	key_id = os.environ["OAUTH_TOKEN_KMS_KEY_ID"]
	resp = _kms_client().encrypt(KeyId=key_id, Plaintext=plaintext.encode("utf-8"))
	return base64.b64encode(resp["CiphertextBlob"]).decode("ascii")


def decrypt_refresh_token(ciphertext_b64: str) -> str:
	"""Reverse of encrypt_refresh_token."""
	ciphertext = base64.b64decode(ciphertext_b64.encode("ascii"))
	resp = _kms_client().decrypt(CiphertextBlob=ciphertext)
	return resp["Plaintext"].decode("utf-8")


def _build_flow() -> Flow:
	client_config = {
		"web": {
			"client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
			"client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
			"auth_uri": "https://accounts.google.com/o/oauth2/auth",
			"token_uri": "https://oauth2.googleapis.com/token",
			"redirect_uris": [os.environ["GOOGLE_OAUTH_REDIRECT_URI"]],
		}
	}
	flow = Flow.from_client_config(client_config, scopes=OAUTH_SCOPES)
	flow.redirect_uri = os.environ["GOOGLE_OAUTH_REDIRECT_URI"]
	return flow


def build_consent_url(user_id: str) -> tuple[str, str]:
	"""Return (consent_url, state). State must be persisted and verified on callback."""
	state = secrets.token_urlsafe(32)
	flow = _build_flow()
	url, _ = flow.authorization_url(
		access_type="offline",
		include_granted_scopes="true",
		prompt="consent",
		state=state,
	)
	return url, state


def exchange_code_for_credentials(code: str) -> Dict:
	"""Exchange authorization code for tokens. Returns dict with access_token, refresh_token, expiry, scopes."""
	flow = _build_flow()
	flow.fetch_token(code=code)
	creds = flow.credentials
	return {
		"access_token": creds.token,
		"refresh_token": creds.refresh_token,
		"expiry": creds.expiry.isoformat() if creds.expiry else None,
		"scopes": list(creds.scopes or []),
	}

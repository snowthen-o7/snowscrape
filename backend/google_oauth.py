"""
Google OAuth flow helpers.
Handles consent URL generation, code-for-token exchange, token refresh,
and KMS encryption/decryption of refresh tokens.
"""
import base64
import os
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

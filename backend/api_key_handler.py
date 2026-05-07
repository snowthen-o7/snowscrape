"""
Lambda handlers for API key management.
Users can create, list, and revoke API keys for programmatic access.
"""

import hashlib
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone

from connection_pool import get_table
from logger import get_logger, log_lambda_invocation
from utils import extract_token_from_event, validate_clerk_token

logger = get_logger(__name__)

API_KEY_PREFIX = "sk_live_"
API_KEY_LENGTH = 32  # random chars after prefix

# CORS helper
_CORS_ALLOWED_ORIGINS = set(
	o.strip()
	for o in os.environ.get("CORS_ALLOWED_ORIGIN", "http://localhost:3001").split(",")
	if o.strip()
)


def _cors_origin(event=None):
	if event:
		headers = event.get("headers", {}) or {}
		origin = headers.get("origin") or headers.get("Origin", "")
		if origin in _CORS_ALLOWED_ORIGINS:
			return origin
	return next(iter(_CORS_ALLOWED_ORIGINS))


def _response(status, body, event=None):
	return {
		"statusCode": status,
		"body": json.dumps(body),
		"headers": {
			"Content-Type": "application/json",
			"Access-Control-Allow-Origin": _cors_origin(event),
			"Access-Control-Allow-Credentials": True,
		},
	}


def _authenticate(event):
	"""Extract and validate Clerk token. Returns (user_data, error_response)."""
	token = extract_token_from_event(event)
	if not token:
		return None, _response(401, {"message": "Unauthorized"}, event)
	try:
		user_data = validate_clerk_token(token)
		return user_data, None
	except Exception as e:
		return None, _response(401, {"message": str(e)}, event)


def _get_api_keys_table():
	table_name = os.environ.get("DYNAMODB_API_KEYS_TABLE", "")
	if not table_name:
		raise RuntimeError("DYNAMODB_API_KEYS_TABLE not configured")
	return get_table(table_name)


def _hash_key(raw_key: str) -> str:
	"""SHA-256 hash of the raw API key."""
	return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# ─── Create API Key ──────────────────────────────────────────────────────────

def create_api_key_handler(event, context):
	"""POST /api-keys — Generate a new API key."""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err

	user_id = user_data["sub"]

	try:
		body = json.loads(event.get("body") or "{}")
		name = body.get("name", "").strip()
		if not name:
			return _response(400, {"message": "API key name is required"}, event)
		if len(name) > 100:
			return _response(400, {"message": "Name must be 100 characters or less"}, event)

		# Check key count limit (max 10 per user)
		table = _get_api_keys_table()
		existing = table.query(
			IndexName="UserIdIndex",
			KeyConditionExpression="user_id = :uid",
			ExpressionAttributeValues={":uid": user_id},
			Select="COUNT",
		)
		if existing.get("Count", 0) >= 10:
			return _response(400, {
				"message": "Maximum 10 API keys per account"
			}, event)

		# Generate key
		raw_key = API_KEY_PREFIX + secrets.token_urlsafe(API_KEY_LENGTH)
		key_hash = _hash_key(raw_key)
		key_prefix = raw_key[:12]  # "sk_live_XXXX" for display
		api_key_id = str(uuid.uuid4())
		now = datetime.now(timezone.utc).isoformat()

		table.put_item(Item={
			"api_key_id": api_key_id,
			"user_id": user_id,
			"name": name,
			"key_hash": key_hash,
			"key_prefix": key_prefix,
			"created_at": now,
			"last_used_at": None,
			"is_active": True,
		})

		logger.info("API key created",
					 user_id=user_id, api_key_id=api_key_id, name=name)

		# Return the FULL key exactly once — it's never stored in plaintext
		return _response(201, {
			"api_key_id": api_key_id,
			"name": name,
			"key": raw_key,
			"key_prefix": key_prefix,
			"created_at": now,
			"message": "Save this key now — it won't be shown again.",
		}, event)

	except Exception as e:
		logger.error("Failed to create API key", error=e, user_id=user_id)
		return _response(500, {"message": "Failed to create API key"}, event)


# ─── List API Keys ───────────────────────────────────────────────────────────

def list_api_keys_handler(event, context):
	"""GET /api-keys — List all API keys for the current user."""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err

	user_id = user_data["sub"]

	try:
		table = _get_api_keys_table()
		response = table.query(
			IndexName="UserIdIndex",
			KeyConditionExpression="user_id = :uid",
			ExpressionAttributeValues={":uid": user_id},
		)

		keys = []
		for item in response.get("Items", []):
			keys.append({
				"api_key_id": item["api_key_id"],
				"name": item.get("name", ""),
				"key_prefix": item.get("key_prefix", ""),
				"created_at": item.get("created_at", ""),
				"last_used_at": item.get("last_used_at"),
				"is_active": item.get("is_active", True),
			})

		# Sort by created_at descending
		keys.sort(key=lambda k: k.get("created_at", ""), reverse=True)

		return _response(200, {"keys": keys}, event)

	except Exception as e:
		logger.error("Failed to list API keys", error=e, user_id=user_id)
		return _response(500, {"message": "Failed to list API keys"}, event)


# ─── Delete API Key ──────────────────────────────────────────────────────────

def delete_api_key_handler(event, context):
	"""DELETE /api-keys/{api_key_id} — Revoke an API key (soft delete)."""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err

	user_id = user_data["sub"]
	api_key_id = event.get("pathParameters", {}).get("api_key_id", "")

	if not api_key_id:
		return _response(400, {"message": "api_key_id is required"}, event)

	try:
		table = _get_api_keys_table()

		# Fetch key and verify ownership
		response = table.get_item(Key={"api_key_id": api_key_id})
		item = response.get("Item")

		if not item:
			return _response(404, {"message": "API key not found"}, event)
		if item.get("user_id") != user_id:
			return _response(403, {"message": "Not authorized"}, event)

		# Soft delete
		table.update_item(
			Key={"api_key_id": api_key_id},
			UpdateExpression="SET is_active = :inactive",
			ExpressionAttributeValues={":inactive": False},
		)

		logger.info("API key revoked",
					 user_id=user_id, api_key_id=api_key_id)
		return _response(200, {"message": "API key revoked"}, event)

	except Exception as e:
		logger.error("Failed to delete API key", error=e,
					 user_id=user_id, api_key_id=api_key_id)
		return _response(500, {"message": "Failed to revoke API key"}, event)


# ─── Validate API Key (utility, not a handler) ───────────────────────────────

def validate_api_key(raw_key: str) -> dict | None:
	"""
	Validate an API key by hashing and looking up in DynamoDB.
	Updates last_used_at timestamp.

	Returns:
		User data dict with user_id, or None if invalid.
	"""
	if not raw_key or not raw_key.startswith(API_KEY_PREFIX):
		return None

	key_hash = _hash_key(raw_key)

	try:
		table = _get_api_keys_table()
		response = table.query(
			IndexName="KeyHashIndex",
			KeyConditionExpression="key_hash = :hash",
			ExpressionAttributeValues={":hash": key_hash},
			Limit=1,
		)

		items = response.get("Items", [])
		if not items:
			return None

		key_record = items[0]
		if not key_record.get("is_active", False):
			return None

		# Update last_used_at (fire-and-forget)
		try:
			table.update_item(
				Key={"api_key_id": key_record["api_key_id"]},
				UpdateExpression="SET last_used_at = :now",
				ExpressionAttributeValues={
					":now": datetime.now(timezone.utc).isoformat(),
				},
			)
		except Exception:
			pass  # Non-critical

		return {"user_id": key_record["user_id"], "api_key_id": key_record["api_key_id"]}

	except Exception as e:
		logger.error("API key validation failed", error=e)
		return None

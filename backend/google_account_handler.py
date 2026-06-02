"""HTTP handlers for /integrations/google/*."""
import json
import os
from datetime import datetime, timezone

from connection_pool import get_table
from google_oauth import (
	build_consent_url,
	encrypt_refresh_token,
	exchange_code_for_credentials,
	fetch_google_user_info,
)
from logger import get_logger, log_lambda_invocation
from utils import extract_token_from_event, validate_clerk_token

logger = get_logger(__name__)

_CORS_ALLOWED_ORIGINS = set(
	o.strip()
	for o in os.environ.get("CORS_ALLOWED_ORIGIN", "http://localhost:3001").split(",")
	if o.strip()
)


def _cors_origin(event):
	headers = (event or {}).get("headers") or {}
	origin = headers.get("origin") or headers.get("Origin", "")
	if origin in _CORS_ALLOWED_ORIGINS:
		return origin
	return next(iter(_CORS_ALLOWED_ORIGINS))


def _response(status, body, event=None):
	if status == 204:
		return {"statusCode": 204, "body": "", "headers": _headers(event)}
	return {"statusCode": status, "body": json.dumps(body), "headers": _headers(event)}


def _headers(event):
	return {
		"Content-Type": "application/json",
		"Access-Control-Allow-Origin": _cors_origin(event),
		"Access-Control-Allow-Credentials": True,
	}


def _authenticate(event):
	token = extract_token_from_event(event)
	if not token:
		return None, _response(401, {"message": "Unauthorized"}, event)
	try:
		user_data = validate_clerk_token(token)
		return user_data, None
	except Exception as e:
		return None, _response(401, {"message": str(e)}, event)


def _table():
	return get_table(os.environ["DYNAMODB_GOOGLE_ACCOUNTS_TABLE"])


def get_auth_url_handler(event, context):
	"""GET /integrations/google/auth-url"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	url, state = build_consent_url(user_id=user_data["sub"])
	return _response(200, {"auth_url": url, "state": state}, event)


def oauth_callback_handler(event, context):
	"""POST /integrations/google/callback {code, state}"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	body = json.loads(event.get("body") or "{}")
	code = body.get("code")
	if not code:
		return _response(400, {"message": "code is required"}, event)
	try:
		creds = exchange_code_for_credentials(code=code)
	except Exception as e:
		logger.error("OAuth token exchange failed", error=str(e))
		return _response(400, {"message": "Failed to exchange code"}, event)

	if not creds.get("refresh_token"):
		return _response(400, {"message": "No refresh token returned; user must re-consent"}, event)

	user_info = fetch_google_user_info(creds["access_token"])
	ciphertext = encrypt_refresh_token(creds["refresh_token"])

	_table().put_item(Item={
		"user_id": user_data["sub"],
		"google_user_id": user_info["google_user_id"],
		"email": user_info["email"],
		"name": user_info["name"],
		"refresh_token_ciphertext": ciphertext,
		"scopes": creds["scopes"],
		"connected_at": datetime.now(timezone.utc).isoformat(),
	})
	return _response(200, {"email": user_info["email"], "name": user_info["name"]}, event)


def list_google_accounts_handler(event, context):
	"""GET /integrations/google"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	item = _table().get_item(Key={"user_id": user_data["sub"]}).get("Item")
	if not item:
		return _response(200, {"accounts": []}, event)
	return _response(200, {"accounts": [{
		"google_user_id": item["google_user_id"],
		"email": item["email"],
		"name": item.get("name", ""),
		"connected_at": item.get("connected_at"),
	}]}, event)


def revoke_google_account_handler(event, context):
	"""DELETE /integrations/google"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	_table().delete_item(Key={"user_id": user_data["sub"]})
	return _response(204, None, event)

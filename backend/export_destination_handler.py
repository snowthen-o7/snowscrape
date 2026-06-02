"""HTTP handlers for /export-destinations."""
import json
import os
import uuid
from datetime import datetime, timezone

from connection_pool import get_table
from logger import get_logger, log_lambda_invocation
from utils import extract_token_from_event, validate_clerk_token

logger = get_logger(__name__)

VALID_TYPES = {"google_docs"}
VALID_MODES = {"new_doc_per_run", "one_doc_per_row"}
VALID_FORMATS = {"structured_log", "compact_list", "narrative"}
MAX_NAME_LEN = 100
MAX_TEMPLATE_LEN = 200

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


def _headers(event):
	return {
		"Content-Type": "application/json",
		"Access-Control-Allow-Origin": _cors_origin(event),
		"Access-Control-Allow-Credentials": True,
	}


def _response(status, body, event=None):
	if status == 204:
		return {"statusCode": 204, "body": "", "headers": _headers(event)}
	return {"statusCode": status, "body": json.dumps(body), "headers": _headers(event)}


def _authenticate(event):
	token = extract_token_from_event(event)
	if not token:
		return None, _response(401, {"message": "Unauthorized"}, event)
	try:
		return validate_clerk_token(token), None
	except Exception as e:
		return None, _response(401, {"message": str(e)}, event)


def _destinations_table():
	return get_table(os.environ["DYNAMODB_EXPORT_DESTINATIONS_TABLE"])


def _google_accounts_table():
	return get_table(os.environ["DYNAMODB_GOOGLE_ACCOUNTS_TABLE"])


def _validate_body(body):
	name = (body.get("name") or "").strip()
	if not name or len(name) > MAX_NAME_LEN:
		return f"name must be 1-{MAX_NAME_LEN} chars"
	if body.get("type") not in VALID_TYPES:
		return f"type must be one of {sorted(VALID_TYPES)}"
	if not body.get("drive_folder_id"):
		return "drive_folder_id is required"
	tmpl = body.get("naming_template", "")
	if not tmpl or len(tmpl) > MAX_TEMPLATE_LEN:
		return f"naming_template must be 1-{MAX_TEMPLATE_LEN} chars"
	if body.get("mode") not in VALID_MODES:
		return f"mode must be one of {sorted(VALID_MODES)}"
	if body.get("format_template") not in VALID_FORMATS:
		return f"format_template must be one of {sorted(VALID_FORMATS)}"
	return None


def create_destination_handler(event, context):
	"""POST /export-destinations"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	user_id = user_data["sub"]
	body = json.loads(event.get("body") or "{}")
	msg = _validate_body(body)
	if msg:
		return _response(400, {"message": msg}, event)

	account = _google_accounts_table().get_item(Key={"user_id": user_id}).get("Item")
	if not account:
		return _response(400, {"message": "No Google account connected. Connect one first."}, event)

	destination_id = f"dst_{uuid.uuid4().hex[:16]}"
	item = {
		"destination_id": destination_id,
		"user_id": user_id,
		"name": body["name"].strip(),
		"type": body["type"],
		"google_user_id": account["google_user_id"],
		"drive_folder_id": body["drive_folder_id"],
		"naming_template": body["naming_template"],
		"mode": body["mode"],
		"format_template": body["format_template"],
		"created_at": datetime.now(timezone.utc).isoformat(),
	}
	_destinations_table().put_item(Item=item)
	return _response(201, item, event)


def list_destinations_handler(event, context):
	"""GET /export-destinations"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	resp = _destinations_table().query(
		IndexName="UserIdIndex",
		KeyConditionExpression="user_id = :uid",
		ExpressionAttributeValues={":uid": user_data["sub"]},
	)
	return _response(200, {"destinations": resp.get("Items", [])}, event)


def delete_destination_handler(event, context):
	"""DELETE /export-destinations/{destination_id}"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	destination_id = (event.get("pathParameters") or {}).get("destination_id")
	if not destination_id:
		return _response(400, {"message": "destination_id required"}, event)
	existing = _destinations_table().get_item(Key={"destination_id": destination_id}).get("Item")
	if not existing or existing.get("user_id") != user_data["sub"]:
		return _response(404, {"message": "Destination not found"}, event)
	_destinations_table().delete_item(Key={"destination_id": destination_id})
	return _response(204, None, event)

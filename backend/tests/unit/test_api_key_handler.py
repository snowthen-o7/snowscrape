"""Unit tests for api_key_handler.

Covers the programmatic-API key lifecycle handlers (create / list / delete) and
the `validate_api_key` auth chokepoint that `utils.resolve_user_id` calls to
authenticate `sk_live_...` Bearer keys on the /jobs data-plane. A silent
regression here is either an auth bypass (a revoked key still authenticating) or
broken programmatic access, so these pin the security-relevant contracts:
plaintext keys are never stored, revoked/inactive keys never validate, and
ownership is enforced on delete.

Characterization only: no source change. Uses the conftest `dynamodb_client`
fixture (creates SnowscrapeApiKeys-test with the UserIdIndex + KeyHashIndex GSIs)
and mocks Clerk auth via `validate_clerk_token`.
"""
import hashlib
import json
from datetime import datetime
from unittest.mock import patch

import pytest


API_KEYS_TABLE = "SnowscrapeApiKeys-test"
USER = "user_abc"


def _event(body=None, path_params=None, with_auth=True):
	headers = {"origin": "http://localhost:3001"}
	if with_auth:
		headers["Authorization"] = "Bearer clerk-token"
	return {
		"headers": headers,
		"body": json.dumps(body) if body is not None else None,
		"pathParameters": path_params or {},
	}


def _sha256(raw):
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _put_key(dynamodb_client, *, api_key_id, user_id=USER, key_hash="h", is_active=True,
			 created_at="2026-01-01T00:00:00+00:00", name="k", include_active=True):
	item = {
		"api_key_id": api_key_id,
		"user_id": user_id,
		"key_hash": key_hash,
		"key_prefix": "sk_live_xxxx",
		"name": name,
		"created_at": created_at,
		"last_used_at": None,
	}
	if include_active:
		item["is_active"] = is_active
	dynamodb_client.Table(API_KEYS_TABLE).put_item(Item=item)


# ─── create_api_key_handler ──────────────────────────────────────────────────

def test_create_requires_auth(dynamodb_client, lambda_context):
	from api_key_handler import create_api_key_handler
	resp = create_api_key_handler(_event({"name": "k"}, with_auth=False), lambda_context)
	assert resp["statusCode"] == 401


@patch("api_key_handler.validate_clerk_token", side_effect=Exception("bad token"))
def test_create_401_on_invalid_token(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import create_api_key_handler
	resp = create_api_key_handler(_event({"name": "k"}), lambda_context)
	assert resp["statusCode"] == 401
	assert json.loads(resp["body"])["message"] == "bad token"


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_create_400_on_missing_name(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import create_api_key_handler
	# empty body, empty string, and whitespace-only all fail the required-name guard
	for body in ({}, {"name": ""}, {"name": "   "}):
		resp = create_api_key_handler(_event(body), lambda_context)
		assert resp["statusCode"] == 400
		assert "name is required" in json.loads(resp["body"])["message"]


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_create_400_on_name_too_long(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import create_api_key_handler
	resp = create_api_key_handler(_event({"name": "x" * 101}), lambda_context)
	assert resp["statusCode"] == 400
	assert "100 characters or less" in json.loads(resp["body"])["message"]
	# boundary: exactly 100 is allowed
	ok = create_api_key_handler(_event({"name": "y" * 100}), lambda_context)
	assert ok["statusCode"] == 201


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_create_enforces_10_key_cap(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import create_api_key_handler
	for i in range(10):
		_put_key(dynamodb_client, api_key_id=f"k{i}")
	resp = create_api_key_handler(_event({"name": "k11"}), lambda_context)
	assert resp["statusCode"] == 400
	assert "Maximum 10 API keys" in json.loads(resp["body"])["message"]
	# the rejected create wrote nothing: still exactly 10 rows
	assert dynamodb_client.Table(API_KEYS_TABLE).scan()["Count"] == 10


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_create_allows_10th_key_when_9_exist(_clerk, dynamodb_client, lambda_context):
	"""Boundary: the cap is `>= 10`, so a 10th key (9 already present) is allowed."""
	from api_key_handler import create_api_key_handler
	for i in range(9):
		_put_key(dynamodb_client, api_key_id=f"k{i}")
	resp = create_api_key_handler(_event({"name": "the-tenth"}), lambda_context)
	assert resp["statusCode"] == 201
	assert dynamodb_client.Table(API_KEYS_TABLE).scan()["Count"] == 10


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_create_happy_path_returns_raw_key_and_persists_hash_only(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import create_api_key_handler, API_KEY_PREFIX
	resp = create_api_key_handler(_event({"name": "My CI key"}), lambda_context)
	assert resp["statusCode"] == 201
	body = json.loads(resp["body"])

	raw = body["key"]
	assert raw.startswith(API_KEY_PREFIX)
	assert body["key_prefix"] == raw[:12]
	assert body["name"] == "My CI key"
	assert "api_key_id" in body and "created_at" in body

	# Stored row: hashed, never plaintext; defaults pinned.
	items = dynamodb_client.Table(API_KEYS_TABLE).scan()["Items"]
	assert len(items) == 1
	stored = items[0]
	assert stored["user_id"] == USER
	assert stored["key_hash"] == _sha256(raw)
	assert stored["key_hash"] != raw            # hashed, not the raw key
	assert "key" not in stored                  # plaintext key never persisted
	assert stored["is_active"] is True
	assert stored["last_used_at"] is None
	assert stored["key_prefix"] == raw[:12]


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_create_500_when_table_errors(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import create_api_key_handler
	with patch("api_key_handler._get_api_keys_table", side_effect=RuntimeError("boom")):
		resp = create_api_key_handler(_event({"name": "k"}), lambda_context)
	assert resp["statusCode"] == 500
	assert json.loads(resp["body"])["message"] == "Failed to create API key"


# ─── list_api_keys_handler ───────────────────────────────────────────────────

def test_list_requires_auth(dynamodb_client, lambda_context):
	from api_key_handler import list_api_keys_handler
	resp = list_api_keys_handler(_event(with_auth=False), lambda_context)
	assert resp["statusCode"] == 401


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_list_empty(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import list_api_keys_handler
	resp = list_api_keys_handler(_event(), lambda_context)
	assert resp["statusCode"] == 200
	assert json.loads(resp["body"])["keys"] == []


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_list_scopes_to_user_sorts_desc_and_omits_hash(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import list_api_keys_handler
	_put_key(dynamodb_client, api_key_id="old", created_at="2026-01-01T00:00:00+00:00", key_hash="h-old")
	_put_key(dynamodb_client, api_key_id="new", created_at="2026-03-01T00:00:00+00:00", key_hash="h-new")
	_put_key(dynamodb_client, api_key_id="other", user_id="someone_else", key_hash="h-other")

	resp = list_api_keys_handler(_event(), lambda_context)
	assert resp["statusCode"] == 200
	keys = json.loads(resp["body"])["keys"]

	ids = [k["api_key_id"] for k in keys]
	assert ids == ["new", "old"]                       # this user only, created_at desc
	# the secret hash is never exposed in a list response
	assert all("key_hash" not in k and "key" not in k for k in keys)


# ─── delete_api_key_handler ──────────────────────────────────────────────────

def test_delete_requires_auth(dynamodb_client, lambda_context):
	from api_key_handler import delete_api_key_handler
	resp = delete_api_key_handler(_event(path_params={"api_key_id": "x"}, with_auth=False), lambda_context)
	assert resp["statusCode"] == 401


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_delete_400_without_id(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import delete_api_key_handler
	resp = delete_api_key_handler(_event(path_params={}), lambda_context)
	assert resp["statusCode"] == 400


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_delete_404_when_missing(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import delete_api_key_handler
	resp = delete_api_key_handler(_event(path_params={"api_key_id": "nope"}), lambda_context)
	assert resp["statusCode"] == 404


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_delete_403_when_not_owner(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import delete_api_key_handler
	_put_key(dynamodb_client, api_key_id="someone-elses", user_id="other_user")
	resp = delete_api_key_handler(_event(path_params={"api_key_id": "someone-elses"}), lambda_context)
	assert resp["statusCode"] == 403
	# ownership guard must not have flipped the victim's key inactive
	row = dynamodb_client.Table(API_KEYS_TABLE).get_item(Key={"api_key_id": "someone-elses"})["Item"]
	assert row["is_active"] is True


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_delete_is_soft_delete(_clerk, dynamodb_client, lambda_context):
	from api_key_handler import delete_api_key_handler
	_put_key(dynamodb_client, api_key_id="mine")
	resp = delete_api_key_handler(_event(path_params={"api_key_id": "mine"}), lambda_context)
	assert resp["statusCode"] == 200
	# row still present (soft delete), is_active flipped to False
	row = dynamodb_client.Table(API_KEYS_TABLE).get_item(Key={"api_key_id": "mine"})["Item"]
	assert row["is_active"] is False


# ─── validate_api_key (auth chokepoint) ──────────────────────────────────────

def test_validate_none_on_empty_or_missing_prefix(dynamodb_client):
	from api_key_handler import validate_api_key
	assert validate_api_key("") is None
	assert validate_api_key(None) is None
	assert validate_api_key("not-a-snowscrape-key") is None
	assert validate_api_key("Bearer sk_live_abc") is None   # prefix must lead the string


def test_validate_none_when_hash_unknown(dynamodb_client):
	from api_key_handler import validate_api_key
	assert validate_api_key("sk_live_unknownkey") is None


def test_validate_returns_user_and_updates_last_used(dynamodb_client):
	from api_key_handler import validate_api_key
	raw = "sk_live_realkey123"
	_put_key(dynamodb_client, api_key_id="kid-1", key_hash=_sha256(raw), is_active=True)

	result = validate_api_key(raw)
	assert result == {"user_id": USER, "api_key_id": "kid-1"}

	# last_used_at is stamped with a fresh ISO timestamp on a successful validation (was None)
	row = dynamodb_client.Table(API_KEYS_TABLE).get_item(Key={"api_key_id": "kid-1"})["Item"]
	assert row["last_used_at"] is not None
	datetime.fromisoformat(row["last_used_at"])   # parses as ISO-8601, not a sentinel/garbage value


def test_validate_last_used_update_failure_is_non_fatal(dynamodb_client):
	"""A failing last_used_at update must NOT fail validation (fire-and-forget contract)."""
	from api_key_handler import validate_api_key
	raw = "sk_live_nonfatalkey"
	_put_key(dynamodb_client, api_key_id="kid-nf", key_hash=_sha256(raw), is_active=True)

	real = dynamodb_client.Table(API_KEYS_TABLE)

	class _UpdateRaises:
		def query(self, **kw):
			return real.query(**kw)

		def update_item(self, **kw):
			raise RuntimeError("ddb update unavailable")

	with patch("api_key_handler._get_api_keys_table", return_value=_UpdateRaises()):
		result = validate_api_key(raw)
	assert result == {"user_id": USER, "api_key_id": "kid-nf"}


def test_validate_rejects_inactive_key(dynamodb_client):
	"""A revoked (soft-deleted) key must not authenticate."""
	from api_key_handler import validate_api_key
	raw = "sk_live_revokedkey"
	_put_key(dynamodb_client, api_key_id="kid-revoked", key_hash=_sha256(raw), is_active=False)
	assert validate_api_key(raw) is None


def test_validate_rejects_key_without_active_flag(dynamodb_client):
	"""A row missing is_active is treated as inactive (default False), so it never authenticates."""
	from api_key_handler import validate_api_key
	raw = "sk_live_noflagkey"
	_put_key(dynamodb_client, api_key_id="kid-noflag", key_hash=_sha256(raw), include_active=False)
	assert validate_api_key(raw) is None


@patch("api_key_handler.validate_clerk_token", return_value={"sub": USER})
def test_create_then_validate_then_revoke_then_reject(_clerk, dynamodb_client, lambda_context):
	"""End-to-end: a freshly created key authenticates, and stops authenticating after a delete."""
	from api_key_handler import create_api_key_handler, delete_api_key_handler, validate_api_key

	created = json.loads(create_api_key_handler(_event({"name": "lifecycle"}), lambda_context)["body"])
	raw = created["key"]
	key_id = created["api_key_id"]

	assert validate_api_key(raw) == {"user_id": USER, "api_key_id": key_id}

	delete_resp = delete_api_key_handler(_event(path_params={"api_key_id": key_id}), lambda_context)
	assert delete_resp["statusCode"] == 200
	assert validate_api_key(raw) is None


# ─── CORS ────────────────────────────────────────────────────────────────────

def test_cors_does_not_reflect_untrusted_origin(dynamodb_client, lambda_context):
	"""An origin outside the allowlist is never echoed back (responses also send
	Allow-Credentials: true, so reflecting an arbitrary origin would be a real vuln)."""
	from api_key_handler import list_api_keys_handler
	evt = _event(with_auth=False)
	evt["headers"]["origin"] = "https://evil.example"
	resp = list_api_keys_handler(evt, lambda_context)
	assert resp["headers"]["Access-Control-Allow-Origin"] != "https://evil.example"

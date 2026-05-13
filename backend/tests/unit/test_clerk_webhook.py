"""Unit tests for clerk_webhook_handler.py.

Covers:
- Signature verification: invalid → 400, valid → 200
- Idempotency: duplicate event_id → 200 without dispatch
- Rollback: dispatch exception → dedup row deleted, 500 returned
- No-op for unhandled event types (user.created, etc.)
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def clerk_user_deleted_payload():
	"""Minimal user.deleted Clerk event payload (post-verification dict)."""
	return {
		"id": "msg_clerk_001",
		"type": "user.deleted",
		"data": {"id": "user-del-1", "deleted": True},
	}


@pytest.fixture
def clerk_user_created_payload():
	return {
		"id": "msg_clerk_002",
		"type": "user.created",
		"data": {"id": "user-new-1"},
	}


def _make_event(payload_dict, svix_id="msg_clerk_001"):
	"""Build a Lambda API GW event wrapping a Clerk webhook body."""
	return {
		"body": json.dumps(payload_dict),
		"isBase64Encoded": False,
		"headers": {
			"svix-id": svix_id,
			"svix-timestamp": "1234567890",
			"svix-signature": "v1,fakesignature",
		},
	}


def _patch_svix_verify(payload_dict):
	"""Context manager that makes Webhook.verify return payload_dict."""
	mock_wh_instance = MagicMock()
	mock_wh_instance.verify.return_value = payload_dict
	mock_wh_class = MagicMock(return_value=mock_wh_instance)
	# Patch the module-level name in clerk_webhook_handler
	return patch("clerk_webhook_handler.Webhook", mock_wh_class)


def _patch_svix_invalid():
	"""Context manager that makes Webhook.verify raise WebhookVerificationError."""
	from svix.webhooks import WebhookVerificationError

	mock_wh_instance = MagicMock()
	mock_wh_instance.verify.side_effect = WebhookVerificationError("bad sig")
	mock_wh_class = MagicMock(return_value=mock_wh_instance)
	return patch("clerk_webhook_handler.Webhook", mock_wh_class)


# ─── Signature Verification ───────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.aws
class TestSignatureVerification:
	def test_invalid_signature_returns_400(
		self, dynamodb_client, mock_env_vars, lambda_context,
		clerk_user_deleted_payload
	):
		os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_test"
		from clerk_webhook_handler import handle_clerk_webhook
		event = _make_event(clerk_user_deleted_payload)
		with _patch_svix_invalid():
			resp = handle_clerk_webhook(event, lambda_context)
		assert resp["statusCode"] == 400
		assert "signature" in resp["body"].lower() or "invalid" in resp["body"].lower()

	def test_valid_signature_processes_event_and_returns_200(
		self, dynamodb_client, mock_env_vars, lambda_context,
		clerk_user_deleted_payload
	):
		os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_test"
		from clerk_webhook_handler import handle_clerk_webhook
		event = _make_event(clerk_user_deleted_payload)
		with _patch_svix_verify(clerk_user_deleted_payload):
			with patch("clerk_webhook_handler._handle_user_deleted") as mock_handler:
				resp = handle_clerk_webhook(event, lambda_context)
		assert resp["statusCode"] == 200
		mock_handler.assert_called_once_with(clerk_user_deleted_payload["data"])


# ─── Idempotency ──────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.aws
class TestIdempotency:
	def test_duplicate_event_returns_200_without_dispatch(
		self, dynamodb_client, mock_env_vars, lambda_context,
		clerk_user_deleted_payload
	):
		os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_test"
		# Pre-seed dedup row
		dedup_table = dynamodb_client.Table("SnowscrapeBillingWebhookDedup-test")
		dedup_table.put_item(Item={
			"event_id": "msg_clerk_001",
			"ttl": 9999999999,
			"type": "user.deleted",
		})

		from clerk_webhook_handler import handle_clerk_webhook
		event = _make_event(clerk_user_deleted_payload, svix_id="msg_clerk_001")
		with _patch_svix_verify(clerk_user_deleted_payload):
			with patch("clerk_webhook_handler._handle_user_deleted") as mock_handler:
				resp = handle_clerk_webhook(event, lambda_context)

		assert resp["statusCode"] == 200
		mock_handler.assert_not_called()

	def test_first_event_writes_dedup_row(
		self, dynamodb_client, mock_env_vars, lambda_context,
		clerk_user_deleted_payload
	):
		os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_test"
		from clerk_webhook_handler import handle_clerk_webhook
		event = _make_event(clerk_user_deleted_payload, svix_id="msg_clerk_uniq_1")
		payload_with_id = {**clerk_user_deleted_payload, "id": "msg_clerk_uniq_1"}
		with _patch_svix_verify(payload_with_id):
			with patch("clerk_webhook_handler._handle_user_deleted"):
				resp = handle_clerk_webhook(event, lambda_context)

		assert resp["statusCode"] == 200
		dedup_table = dynamodb_client.Table("SnowscrapeBillingWebhookDedup-test")
		row = dedup_table.get_item(Key={"event_id": "msg_clerk_uniq_1"}).get("Item")
		assert row is not None
		assert row["event_id"] == "msg_clerk_uniq_1"


# ─── Rollback on Dispatch Failure ─────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.aws
class TestDispatchRollback:
	def test_dispatch_exception_rolls_back_dedup_and_returns_500(
		self, dynamodb_client, mock_env_vars, lambda_context,
		clerk_user_deleted_payload
	):
		os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_test"
		from clerk_webhook_handler import handle_clerk_webhook
		event = _make_event(clerk_user_deleted_payload, svix_id="msg_clerk_rollback")
		payload_rb = {**clerk_user_deleted_payload, "id": "msg_clerk_rollback"}
		with _patch_svix_verify(payload_rb):
			with patch(
				"clerk_webhook_handler._handle_user_deleted",
				side_effect=RuntimeError("simulated cascade failure"),
			):
				resp = handle_clerk_webhook(event, lambda_context)

		assert resp["statusCode"] == 500
		# Dedup row must be gone so Clerk can retry
		dedup_table = dynamodb_client.Table("SnowscrapeBillingWebhookDedup-test")
		row = dedup_table.get_item(Key={"event_id": "msg_clerk_rollback"}).get("Item")
		assert row is None


# ─── No-op for Unhandled Events ───────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.aws
class TestUnhandledEventTypes:
	def test_user_created_returns_200_and_does_not_call_cascade(
		self, dynamodb_client, mock_env_vars, lambda_context,
		clerk_user_created_payload
	):
		os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_test"
		from clerk_webhook_handler import handle_clerk_webhook
		event = _make_event(clerk_user_created_payload, svix_id="msg_clerk_created")
		payload_c = {**clerk_user_created_payload, "id": "msg_clerk_created"}
		with _patch_svix_verify(payload_c):
			with patch("clerk_webhook_handler._handle_user_deleted") as mock_cascade:
				resp = handle_clerk_webhook(event, lambda_context)

		assert resp["statusCode"] == 200
		mock_cascade.assert_not_called()

	def test_session_created_returns_200_no_cascade(
		self, dynamodb_client, mock_env_vars, lambda_context
	):
		os.environ["CLERK_WEBHOOK_SECRET"] = "whsec_test"
		payload = {"id": "msg_clerk_sess", "type": "session.created", "data": {}}
		from clerk_webhook_handler import handle_clerk_webhook
		event = _make_event(payload, svix_id="msg_clerk_sess")
		with _patch_svix_verify(payload):
			with patch("clerk_webhook_handler._handle_user_deleted") as mock_cascade:
				resp = handle_clerk_webhook(event, lambda_context)

		assert resp["statusCode"] == 200
		mock_cascade.assert_not_called()

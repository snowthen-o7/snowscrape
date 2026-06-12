"""Unit tests for webhook_delivery_handler.

The webhook delivery Lambda is SQS-triggered and is the outbound integration
surface: it signs each event with an HMAC-SHA256 signature so receivers can
verify authenticity, guards the target URL with the SSRF validator (a webhook
URL is user-supplied, so it must not be allowed to reach internal services),
and reports per-record failures back to SQS via `batchItemFailures` so only the
failed messages are retried. A silent regression here is a security problem (a
forgeable/absent signature, or an SSRF bypass) or a reliability problem (a
failed delivery that is never retried, or a successful one retried forever).

Characterization only: no source change. `deliver_webhook` touches no DynamoDB,
so its tests mock `requests.post`; the orchestration tests mock the three
side-effecting helpers; `log_delivery` / `update_webhook_stats` run against the
moto tables created by the conftest `dynamodb_client` fixture.
"""
import hashlib
import hmac
import importlib
import json
import time
from unittest.mock import Mock, patch

import pytest
import requests


@pytest.fixture
def wdh(dynamodb_client):
	"""Import webhook_delivery_handler inside the active moto context.

	The module binds `webhooks_table` / `deliveries_table` at import time from
	`os.environ` + the default DynamoDB resource, so it must be (re)imported
	while moto is active and the env is set (both provided by `dynamodb_client`).
	Reload rebinds the tables to THIS test's fresh moto backend.
	"""
	import webhook_delivery_handler as module
	importlib.reload(module)
	return module


def _resp(status_code=200, text="ok"):
	"""A stand-in requests.Response with just the attributes the code reads."""
	r = Mock()
	r.status_code = status_code
	r.text = text
	return r


def _message(**overrides):
	msg = {
		"delivery_id": "del-1",
		"webhook_id": "wh-1",
		"webhook_url": "https://example.com/hook",
		"webhook_secret": "supersecret",
		"event_type": "job.completed",
		"payload": {"job_id": "j1", "status": "completed"},
	}
	msg.update(overrides)
	return msg


def _record(message=None, message_id="msg-1"):
	return {
		"messageId": message_id,
		"body": json.dumps(message if message is not None else _message()),
	}


# ─── deliver_webhook: SSRF guard ─────────────────────────────────────────────

def test_deliver_blocks_localhost_ssrf_without_posting(wdh):
	"""A localhost target is rejected by the real SSRF validator (offline, no DNS)
	BEFORE any HTTP request is attempted."""
	with patch("webhook_delivery_handler.requests.post") as mock_post:
		success, status_code, body, error = wdh.deliver_webhook(
			webhook_url="http://localhost/hook",
			webhook_secret="s",
			event_type="job.completed",
			delivery_id="del-1",
			payload={"a": 1},
		)
	assert success is False
	assert status_code == 0
	assert body == ""
	assert "SSRF protection" in error
	mock_post.assert_not_called()


def test_deliver_blocks_metadata_ip_ssrf(wdh):
	"""The AWS metadata endpoint (link-local 169.254.169.254) is blocked."""
	with patch("webhook_delivery_handler.requests.post") as mock_post:
		success, status_code, body, error = wdh.deliver_webhook(
			webhook_url="http://169.254.169.254/latest/meta-data/",
			webhook_secret="s",
			event_type="job.completed",
			delivery_id="del-1",
			payload={"a": 1},
		)
	assert success is False
	assert "SSRF protection" in error
	mock_post.assert_not_called()


# ─── deliver_webhook: HMAC signing + headers ─────────────────────────────────

def test_deliver_signs_payload_with_hmac_sha256(wdh):
	payload = {"job_id": "j1", "status": "completed"}
	secret = "supersecret"
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", return_value=_resp(200, "ok")) as mock_post:
		wdh.deliver_webhook(
			webhook_url="https://example.com/hook",
			webhook_secret=secret,
			event_type="job.completed",
			delivery_id="del-1",
			payload=payload,
		)
	_args, kwargs = mock_post.call_args
	sent_body = kwargs["data"]
	# Signature is computed over the EXACT serialized body that is sent.
	expected = hmac.new(secret.encode("utf-8"), sent_body.encode("utf-8"), hashlib.sha256).hexdigest()
	assert kwargs["headers"]["X-Snowscrape-Signature"] == f"sha256={expected}"
	assert sent_body == json.dumps(payload)


def test_deliver_sets_all_event_headers(wdh):
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", return_value=_resp(200, "ok")) as mock_post:
		wdh.deliver_webhook(
			webhook_url="https://example.com/hook",
			webhook_secret="s",
			event_type="job.failed",
			delivery_id="del-xyz",
			payload={"a": 1},
		)
	headers = mock_post.call_args.kwargs["headers"]
	assert headers["Content-Type"] == "application/json"
	assert headers["User-Agent"] == "SnowScrape-Webhooks/1.0"
	assert headers["X-Snowscrape-Event"] == "job.failed"
	assert headers["X-Snowscrape-Delivery-ID"] == "del-xyz"
	# Timestamp is a stringified unix epoch second.
	assert headers["X-Snowscrape-Timestamp"].isdigit()


def test_deliver_omits_signature_when_secret_empty(wdh):
	"""With no secret, no signature header is added (rather than an empty sig)."""
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", return_value=_resp(200, "ok")) as mock_post:
		wdh.deliver_webhook(
			webhook_url="https://example.com/hook",
			webhook_secret="",
			event_type="job.completed",
			delivery_id="del-1",
			payload={"a": 1},
		)
	assert "X-Snowscrape-Signature" not in mock_post.call_args.kwargs["headers"]


def test_deliver_posts_with_30s_timeout(wdh):
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", return_value=_resp(200, "ok")) as mock_post:
		wdh.deliver_webhook("https://example.com/hook", "s", "e", "del-1", {"a": 1})
	assert mock_post.call_args.kwargs["timeout"] == 30


# ─── deliver_webhook: response classification ────────────────────────────────

@pytest.mark.parametrize("status_code", [200, 201, 204, 299])
def test_deliver_treats_2xx_as_success(wdh, status_code):
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", return_value=_resp(status_code, "body")):
		success, code, body, error = wdh.deliver_webhook("https://example.com/hook", "s", "e", "del-1", {"a": 1})
	assert success is True
	assert code == status_code
	assert body == "body"
	assert error is None


@pytest.mark.parametrize("status_code", [301, 302, 400, 404, 500, 503])
def test_deliver_treats_non_2xx_as_failure_but_not_error(wdh, status_code):
	"""A 3xx/4xx/5xx is a delivered-but-unsuccessful response: success False, the
	real status code preserved, and `error` stays None (it is not an exception)."""
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", return_value=_resp(status_code, "nope")):
		success, code, body, error = wdh.deliver_webhook("https://example.com/hook", "s", "e", "del-1", {"a": 1})
	assert success is False
	assert code == status_code
	assert error is None


def test_deliver_truncates_response_body_to_1000_chars(wdh):
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", return_value=_resp(200, "x" * 5000)):
		_success, _code, body, _error = wdh.deliver_webhook("https://example.com/hook", "s", "e", "del-1", {"a": 1})
	assert len(body) == 1000


def test_deliver_empty_response_body_normalized_to_empty_string(wdh):
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", return_value=_resp(200, "")):
		_success, _code, body, _error = wdh.deliver_webhook("https://example.com/hook", "s", "e", "del-1", {"a": 1})
	assert body == ""


# ─── deliver_webhook: network exceptions ─────────────────────────────────────

def test_deliver_timeout_returns_handled_failure(wdh):
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", side_effect=requests.exceptions.Timeout()):
		success, code, body, error = wdh.deliver_webhook("https://example.com/hook", "s", "e", "del-1", {"a": 1})
	assert success is False
	assert code == 0
	assert body == ""
	assert error == "Request timeout"


def test_deliver_connection_error_returns_handled_failure(wdh):
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post",
			   side_effect=requests.exceptions.ConnectionError("dns boom")):
		success, code, body, error = wdh.deliver_webhook("https://example.com/hook", "s", "e", "del-1", {"a": 1})
	assert success is False
	assert code == 0
	assert "dns boom" in error


def test_deliver_unexpected_exception_returns_handled_failure(wdh):
	"""A non-requests exception is still caught and reported, never propagated."""
	with patch("webhook_delivery_handler.validate_scrape_url", return_value="https://example.com/hook"), \
		 patch("webhook_delivery_handler.requests.post", side_effect=ValueError("weird")):
		success, code, body, error = wdh.deliver_webhook("https://example.com/hook", "s", "e", "del-1", {"a": 1})
	assert success is False
	assert "weird" in error


# ─── webhook_delivery_handler: SQS batch orchestration ───────────────────────

def test_handler_successful_delivery_reports_no_failures(wdh, lambda_context):
	with patch("webhook_delivery_handler.deliver_webhook", return_value=(True, 200, "ok", None)) as deliver, \
		 patch("webhook_delivery_handler.log_delivery") as log, \
		 patch("webhook_delivery_handler.update_webhook_stats") as stats:
		result = wdh.webhook_delivery_handler({"Records": [_record()]}, lambda_context)
	assert result == {"batchItemFailures": []}
	deliver.assert_called_once()
	log.assert_called_once()
	stats.assert_called_once_with("wh-1", True)


def test_handler_extracts_message_fields_for_delivery(wdh, lambda_context):
	msg = _message(delivery_id="d9", webhook_id="w9", webhook_url="https://example.com/h",
				   webhook_secret="sek", event_type="job.created", payload={"k": "v"})
	with patch("webhook_delivery_handler.deliver_webhook", return_value=(True, 200, "ok", None)) as deliver, \
		 patch("webhook_delivery_handler.log_delivery"), \
		 patch("webhook_delivery_handler.update_webhook_stats"):
		wdh.webhook_delivery_handler({"Records": [_record(msg)]}, lambda_context)
	kwargs = deliver.call_args.kwargs
	assert kwargs == {
		"webhook_url": "https://example.com/h",
		"webhook_secret": "sek",
		"event_type": "job.created",
		"delivery_id": "d9",
		"payload": {"k": "v"},
	}


def test_handler_failed_delivery_returns_message_id_for_retry(wdh, lambda_context):
	with patch("webhook_delivery_handler.deliver_webhook", return_value=(False, 500, "", "err")), \
		 patch("webhook_delivery_handler.log_delivery"), \
		 patch("webhook_delivery_handler.update_webhook_stats") as stats:
		result = wdh.webhook_delivery_handler({"Records": [_record(message_id="m-fail")]}, lambda_context)
	assert result == {"batchItemFailures": [{"itemIdentifier": "m-fail"}]}
	stats.assert_called_once_with("wh-1", False)


def test_handler_malformed_body_is_caught_and_retried(wdh, lambda_context):
	"""A body that is not valid JSON must not crash the whole batch; the record is
	marked for retry."""
	bad_record = {"messageId": "m-bad", "body": "{not json"}
	with patch("webhook_delivery_handler.deliver_webhook") as deliver:
		result = wdh.webhook_delivery_handler({"Records": [bad_record]}, lambda_context)
	assert result == {"batchItemFailures": [{"itemIdentifier": "m-bad"}]}
	deliver.assert_not_called()


def test_handler_missing_field_is_caught_and_retried(wdh, lambda_context):
	"""A message missing a required key (KeyError on the first access, `delivery_id`)
	is caught per-record rather than crashing the whole batch."""
	incomplete = {}  # no delivery_id/webhook_id/url/secret/event_type/payload
	record = {"messageId": "m-incomplete", "body": json.dumps(incomplete)}
	with patch("webhook_delivery_handler.deliver_webhook") as deliver:
		result = wdh.webhook_delivery_handler({"Records": [record]}, lambda_context)
	assert result == {"batchItemFailures": [{"itemIdentifier": "m-incomplete"}]}
	deliver.assert_not_called()


def test_handler_mixed_batch_only_fails_the_failed_record(wdh, lambda_context):
	records = [
		_record(_message(webhook_id="ok"), message_id="m-ok"),
		_record(_message(webhook_id="bad"), message_id="m-bad"),
	]
	# First record succeeds, second fails.
	with patch("webhook_delivery_handler.deliver_webhook",
			   side_effect=[(True, 200, "ok", None), (False, 500, "", "err")]), \
		 patch("webhook_delivery_handler.log_delivery"), \
		 patch("webhook_delivery_handler.update_webhook_stats"):
		result = wdh.webhook_delivery_handler({"Records": records}, lambda_context)
	assert result == {"batchItemFailures": [{"itemIdentifier": "m-bad"}]}


def test_handler_logs_delivery_even_on_failure(wdh, lambda_context):
	"""A failed delivery is still recorded (log_delivery + stats) before being
	queued for retry, so the failure is observable."""
	with patch("webhook_delivery_handler.deliver_webhook", return_value=(False, 500, "", "err")), \
		 patch("webhook_delivery_handler.log_delivery") as log, \
		 patch("webhook_delivery_handler.update_webhook_stats") as stats:
		wdh.webhook_delivery_handler({"Records": [_record()]}, lambda_context)
	log.assert_called_once()
	stats.assert_called_once_with("wh-1", False)


# ─── log_delivery: DynamoDB write contract (moto) ────────────────────────────

def test_log_delivery_writes_row_with_ttl(wdh):
	before = int(time.time())
	wdh.log_delivery(
		delivery_id="del-77", webhook_id="wh-77", event_type="job.completed",
		webhook_url="https://example.com/hook", success=True, status_code=200,
		response_body="ok", error=None,
	)
	item = wdh.deliveries_table.get_item(Key={"delivery_id": "del-77"})["Item"]
	assert item["webhook_id"] == "wh-77"
	assert item["success"] is True
	assert item["status_code"] == 200
	assert item["response_body"] == "ok"
	assert item["error"] == ""  # None normalized to ''
	# TTL is exactly 30 days after the stored timestamp.
	assert int(item["ttl"]) - int(item["timestamp"]) == 30 * 24 * 60 * 60
	assert int(item["timestamp"]) >= before


def test_log_delivery_normalizes_none_body_and_error(wdh):
	wdh.log_delivery(
		delivery_id="del-78", webhook_id="wh-78", event_type="job.failed",
		webhook_url="https://example.com/hook", success=False, status_code=0,
		response_body=None, error=None,
	)
	item = wdh.deliveries_table.get_item(Key={"delivery_id": "del-78"})["Item"]
	assert item["response_body"] == ""
	assert item["error"] == ""


def test_log_delivery_swallows_write_errors(wdh):
	"""A DynamoDB failure while logging must not propagate (logging is best
	effort; it must never break delivery handling)."""
	with patch.object(wdh.deliveries_table, "put_item", side_effect=Exception("ddb down")):
		# Must not raise.
		wdh.log_delivery(
			delivery_id="del-79", webhook_id="wh-79", event_type="e",
			webhook_url="u", success=True, status_code=200, response_body="", error=None,
		)


# ─── update_webhook_stats: counter contract (moto) ───────────────────────────

def test_update_stats_success_increments_only_total(wdh):
	wdh.update_webhook_stats("wh-stat-1", success=True)
	item = wdh.webhooks_table.get_item(Key={"webhook_id": "wh-stat-1"})["Item"]
	assert int(item["total_deliveries"]) == 1
	assert "failed_deliveries" not in item


def test_update_stats_failure_increments_total_and_failed(wdh):
	wdh.update_webhook_stats("wh-stat-2", success=False)
	item = wdh.webhooks_table.get_item(Key={"webhook_id": "wh-stat-2"})["Item"]
	assert int(item["total_deliveries"]) == 1
	assert int(item["failed_deliveries"]) == 1


def test_update_stats_accumulates_across_calls(wdh):
	wdh.update_webhook_stats("wh-stat-3", success=True)
	wdh.update_webhook_stats("wh-stat-3", success=False)
	wdh.update_webhook_stats("wh-stat-3", success=True)
	item = wdh.webhooks_table.get_item(Key={"webhook_id": "wh-stat-3"})["Item"]
	assert int(item["total_deliveries"]) == 3
	assert int(item["failed_deliveries"]) == 1


def test_update_stats_swallows_write_errors(wdh):
	with patch.object(wdh.webhooks_table, "update_item", side_effect=Exception("ddb down")):
		# Must not raise.
		wdh.update_webhook_stats("wh-stat-4", success=True)

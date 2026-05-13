"""
Lambda handler for Clerk webhook events.
Verifies Svix signatures, deduplicates events, and cascades cleanup
on user.deleted events (cancels Stripe sub + hard-deletes DynamoDB rows).
"""

import json
import os
from datetime import datetime, timezone, timedelta

import stripe
from botocore.exceptions import ClientError
from svix.webhooks import Webhook, WebhookVerificationError

from billing import get_subscription
from connection_pool import get_table
from logger import get_logger, log_lambda_invocation

logger = get_logger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

_DEDUP_TTL_DAYS = 30
_BATCH_SIZE = 25  # DynamoDB BatchWriteItem limit


def _get_dedup_table():
	table_name = os.environ.get("DYNAMODB_BILLING_WEBHOOK_DEDUP_TABLE", "")
	if not table_name:
		raise RuntimeError("DYNAMODB_BILLING_WEBHOOK_DEDUP_TABLE not configured")
	return get_table(table_name)


# ─── Entry Point ──────────────────────────────────────────────────────────────

def handle_clerk_webhook(event, context):
	"""
	POST /clerk/webhook — Idempotent Clerk webhook receiver.
	1. Verify Svix signature (400 on failure).
	2. Conditional-put on event_id to dedup; duplicate → 200 immediately.
	3. Dispatch to _handle_user_deleted on user.deleted; log+200 for others.
	4. On dispatch exception → roll back dedup row and return 500 so Clerk retries.
	"""
	log_lambda_invocation(event, context, logger)

	webhook_secret = os.environ.get("CLERK_WEBHOOK_SECRET", "")
	if not webhook_secret:
		logger.error("CLERK_WEBHOOK_SECRET not configured")
		return {"statusCode": 500, "body": "Webhook secret not configured"}

	body = event.get("body", "") or ""
	if event.get("isBase64Encoded"):
		import base64
		body = base64.b64decode(body).decode("utf-8")

	headers = event.get("headers", {}) or {}
	svix_id = headers.get("svix-id") or headers.get("Svix-Id", "")
	svix_timestamp = headers.get("svix-timestamp") or headers.get("Svix-Timestamp", "")
	svix_signature = headers.get("svix-signature") or headers.get("Svix-Signature", "")

	# Verify Svix signature
	try:
		wh = Webhook(webhook_secret)
		payload = wh.verify(body, {
			"svix-id": svix_id,
			"svix-timestamp": svix_timestamp,
			"svix-signature": svix_signature,
		})
	except Exception:
		logger.warning("Invalid Clerk webhook signature", svix_id=svix_id)
		return {"statusCode": 400, "body": "Invalid signature"}

	# payload is the decoded dict after successful verification
	event_id = svix_id or payload.get("id", "")
	event_type = payload.get("type", "")

	if not event_id:
		logger.error("No event_id found in Clerk webhook")
		return {"statusCode": 400, "body": "Missing event ID"}

	# Idempotency: conditional put on event_id
	dedup_table = _get_dedup_table()
	ttl_epoch = int(
		(datetime.now(timezone.utc) + timedelta(days=_DEDUP_TTL_DAYS)).timestamp()
	)
	try:
		dedup_table.put_item(
			Item={"event_id": event_id, "ttl": ttl_epoch, "type": event_type},
			ConditionExpression="attribute_not_exists(event_id)",
		)
	except ClientError as e:
		if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
			logger.info("Duplicate Clerk webhook ignored",
						event_id=event_id, type=event_type)
			return {"statusCode": 200, "body": "Already processed"}
		logger.error("Dedup put_item failed", error=e, event_id=event_id)
		return {"statusCode": 500, "body": "Dedup failed"}

	logger.info("Clerk webhook received", event_id=event_id, event_type=event_type)

	try:
		if event_type == "user.deleted":
			_handle_user_deleted(payload.get("data", {}))
		else:
			logger.info("Unhandled Clerk event type — no-op", event_type=event_type)
	except Exception as e:
		logger.error("Clerk webhook handler failed", error=e,
					 event_id=event_id, event_type=event_type)
		# Roll back dedup so Clerk can retry
		try:
			dedup_table.delete_item(Key={"event_id": event_id})
		except Exception as rollback_err:
			logger.error("Failed to roll back dedup row", error=rollback_err,
						 event_id=event_id)
		return {"statusCode": 500, "body": "Processing failed"}

	return {"statusCode": 200, "body": "OK"}


# ─── Cascade Handler ──────────────────────────────────────────────────────────

def _handle_user_deleted(data: dict) -> None:
	"""
	Cascade-delete all SnowScrape data for a deleted Clerk user.
	Order: Stripe cancel first (most critical — stops billing), then DB rows.
	"""
	user_id = data.get("id", "")
	if not user_id:
		logger.warning("user.deleted event missing id field", data=data)
		return

	logger.info("Beginning user cascade-delete", user_id=user_id)

	# 1. Cancel Stripe subscription (stops billing before we touch DB)
	sub = get_subscription(user_id)
	stripe_sub_id = sub.get("stripe_subscription_id", "")
	if stripe_sub_id:
		try:
			stripe.Subscription.cancel(stripe_sub_id)
			logger.info("Stripe subscription canceled", user_id=user_id,
						stripe_sub_id=stripe_sub_id)
		except stripe.InvalidRequestError as e:
			if "No such subscription" in str(e):
				logger.info("Stripe subscription already canceled — skipping",
							user_id=user_id, stripe_sub_id=stripe_sub_id)
			else:
				raise

	# 2. Delete from each user-keyed DynamoDB table
	deleted_subscriptions = _delete_subscriptions_row(user_id)
	deleted_api_keys = _delete_api_keys_for_user(user_id)
	job_ids, deleted_jobs = _delete_jobs_for_user(user_id)
	deleted_urls = _delete_urls_for_jobs(job_ids)
	deleted_templates = _delete_templates_for_user(user_id)
	deleted_webhooks, webhook_ids = _delete_webhooks_for_user(user_id)
	deleted_deliveries = _delete_webhook_deliveries_for_user(webhook_ids)

	logger.info(
		"User cascade-delete complete",
		user_id=user_id,
		deleted_subscriptions=deleted_subscriptions,
		deleted_api_keys=deleted_api_keys,
		deleted_jobs=deleted_jobs,
		deleted_urls=deleted_urls,
		deleted_templates=deleted_templates,
		deleted_webhooks=deleted_webhooks,
		deleted_deliveries=deleted_deliveries,
	)


# ─── Per-Table Deletion Helpers ───────────────────────────────────────────────

def _delete_subscriptions_row(user_id: str) -> int:
	"""Delete the single Subscriptions row for this user."""
	try:
		table = get_table(os.environ.get("DYNAMODB_SUBSCRIPTIONS_TABLE", ""))
		table.delete_item(Key={"user_id": user_id})
		logger.info("Deleted subscriptions row", user_id=user_id)
		return 1
	except Exception as e:
		logger.error("Failed to delete subscriptions row", error=e, user_id=user_id)
		raise


def _delete_api_keys_for_user(user_id: str) -> int:
	"""Query UserIdIndex GSI and batch-delete all API keys for this user."""
	try:
		table = get_table(os.environ.get("DYNAMODB_API_KEYS_TABLE", ""))
		items = _scan_gsi(table, "UserIdIndex", "user_id", user_id)
		count = _batch_delete(table, [{"api_key_id": item["api_key_id"]} for item in items])
		logger.info("Deleted API keys", user_id=user_id, count=count)
		return count
	except Exception as e:
		logger.error("Failed to delete API keys", error=e, user_id=user_id)
		raise


def _delete_jobs_for_user(user_id: str) -> tuple[list[str], int]:
	"""Scan Jobs table for this user's jobs, batch-delete, return (job_ids, count)."""
	try:
		table = get_table(os.environ.get("DYNAMODB_JOBS_TABLE", ""))
		items = _scan_filter_user(table, user_id)
		job_ids = [item["job_id"] for item in items]
		count = _batch_delete(table, [{"job_id": job_id} for job_id in job_ids])
		logger.info("Deleted jobs", user_id=user_id, count=count)
		return job_ids, count
	except Exception as e:
		logger.error("Failed to delete jobs", error=e, user_id=user_id)
		raise


def _delete_urls_for_jobs(job_ids: list[str]) -> int:
	"""For each job_id, query Urls table (partition key = job_id) and batch-delete."""
	if not job_ids:
		return 0
	try:
		table = get_table(os.environ.get("DYNAMODB_URLS_TABLE", ""))
		all_keys = []
		for job_id in job_ids:
			response = table.query(
				KeyConditionExpression="job_id = :jid",
				ExpressionAttributeValues={":jid": job_id},
				ProjectionExpression="job_id, #u",
				ExpressionAttributeNames={"#u": "url"},
			)
			items = response.get("Items", [])
			while "LastEvaluatedKey" in response:
				response = table.query(
					KeyConditionExpression="job_id = :jid",
					ExpressionAttributeValues={":jid": job_id},
					ProjectionExpression="job_id, #u",
					ExpressionAttributeNames={"#u": "url"},
					ExclusiveStartKey=response["LastEvaluatedKey"],
				)
				items.extend(response.get("Items", []))
			all_keys.extend([{"job_id": item["job_id"], "url": item["url"]} for item in items])

		count = _batch_delete(table, all_keys)
		logger.info("Deleted URLs", job_count=len(job_ids), url_count=count)
		return count
	except Exception as e:
		logger.error("Failed to delete URLs for jobs", error=e, job_count=len(job_ids))
		raise


def _delete_templates_for_user(user_id: str) -> int:
	"""Scan Templates table and delete all templates for this user."""
	try:
		table = get_table(os.environ.get("DYNAMODB_TEMPLATES_TABLE", ""))
		items = _scan_filter_user(table, user_id)
		count = _batch_delete(table, [{"template_id": item["template_id"]} for item in items])
		logger.info("Deleted templates", user_id=user_id, count=count)
		return count
	except Exception as e:
		logger.error("Failed to delete templates", error=e, user_id=user_id)
		raise


def _delete_webhooks_for_user(user_id: str) -> tuple[int, list[str]]:
	"""Scan Webhooks table and delete all webhooks for this user. Returns (count, webhook_ids)."""
	try:
		table = get_table(os.environ.get("DYNAMODB_WEBHOOKS_TABLE", ""))
		items = _scan_filter_user(table, user_id)
		webhook_ids = [item["webhook_id"] for item in items]
		count = _batch_delete(table, [{"webhook_id": wid} for wid in webhook_ids])
		logger.info("Deleted webhooks", user_id=user_id, count=count)
		return count, webhook_ids
	except Exception as e:
		logger.error("Failed to delete webhooks", error=e, user_id=user_id)
		raise


def _delete_webhook_deliveries_for_user(webhook_ids: list[str]) -> int:
	"""
	For each webhook_id, query WebhookIdIndex GSI and batch-delete deliveries.
	Keyed by webhook_id (not user_id), so we use the webhook_ids collected above.
	"""
	if not webhook_ids:
		return 0
	try:
		table = get_table(os.environ.get("DYNAMODB_WEBHOOK_DELIVERIES_TABLE", ""))
		all_keys = []
		for webhook_id in webhook_ids:
			items = _scan_gsi(table, "WebhookIdIndex", "webhook_id", webhook_id)
			all_keys.extend([{"delivery_id": item["delivery_id"]} for item in items])
		count = _batch_delete(table, all_keys)
		logger.info("Deleted webhook deliveries", webhook_count=len(webhook_ids), count=count)
		return count
	except Exception as e:
		logger.error("Failed to delete webhook deliveries", error=e,
					 webhook_count=len(webhook_ids))
		raise


# ─── Low-level Helpers ────────────────────────────────────────────────────────

def _scan_filter_user(table, user_id: str) -> list[dict]:
	"""Full table scan filtered to a single user_id. Returns all matching items."""
	items = []
	kwargs = {
		"FilterExpression": "user_id = :uid",
		"ExpressionAttributeValues": {":uid": user_id},
		"Select": "ALL_ATTRIBUTES",
	}
	response = table.scan(**kwargs)
	items.extend(response.get("Items", []))
	while "LastEvaluatedKey" in response:
		kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
		response = table.scan(**kwargs)
		items.extend(response.get("Items", []))
	return items


def _scan_gsi(table, index_name: str, key_attr: str, key_value: str) -> list[dict]:
	"""Query a GSI with a single hash key equality condition. Returns all items."""
	items = []
	kwargs = {
		"IndexName": index_name,
		"KeyConditionExpression": f"{key_attr} = :val",
		"ExpressionAttributeValues": {":val": key_value},
	}
	response = table.query(**kwargs)
	items.extend(response.get("Items", []))
	while "LastEvaluatedKey" in response:
		kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
		response = table.query(**kwargs)
		items.extend(response.get("Items", []))
	return items


def _batch_delete(table, keys: list[dict]) -> int:
	"""Delete items in chunks of 25 (DynamoDB BatchWriteItem limit). Returns count deleted."""
	if not keys:
		return 0
	count = 0
	for i in range(0, len(keys), _BATCH_SIZE):
		chunk = keys[i : i + _BATCH_SIZE]
		with table.batch_writer() as batch:
			for key in chunk:
				batch.delete_item(Key=key)
		count += len(chunk)
	return count

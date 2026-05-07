"""
Lambda handlers for Stripe billing endpoints.
Handles checkout sessions, customer portal, webhooks, and usage queries.
"""

import json
import os
import time

import stripe
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError

from billing import (
	PLAN_LIMITS,
	create_or_update_subscription,
	get_subscription,
	reset_all_expired_usage,
)
from connection_pool import get_table
from logger import get_logger, log_lambda_invocation
from utils import extract_token_from_event, validate_clerk_token

logger = get_logger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

_DEDUP_TTL_DAYS = 30


def _get_dedup_table():
	table_name = os.environ.get("DYNAMODB_BILLING_WEBHOOK_DEDUP_TABLE", "")
	if not table_name:
		raise RuntimeError("DYNAMODB_BILLING_WEBHOOK_DEDUP_TABLE not configured")
	return get_table(table_name)


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


# Price ID mapping from env vars
def _get_price_id(plan: str, interval: str = "month") -> str:
	key_map = {
		("pro", "month"): "STRIPE_PRICE_PRO_MONTHLY",
		("business", "month"): "STRIPE_PRICE_BUSINESS_MONTHLY",
	}
	env_key = key_map.get((plan, interval))
	if not env_key:
		raise ValueError(f"No price configured for plan={plan} interval={interval}")
	price_id = os.environ.get(env_key, "")
	if not price_id:
		raise ValueError(f"Price ID not set: {env_key}")
	return price_id


# ─── Checkout Session ─────────────────────────────────────────────────────────

def create_checkout_session_handler(event, context):
	"""POST /billing/checkout — Create a Stripe Checkout Session."""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err

	user_id = user_data["sub"]

	try:
		body_data = json.loads(event.get("body") or "{}")
		plan = body_data.get("plan", "pro")
		interval = body_data.get("interval", "month")
		is_trial = bool(body_data.get("is_trial", False))

		if plan not in ("pro", "business"):
			return _response(400, {"message": "Invalid plan"}, event)
		if interval != "month":
			return _response(400, {"message": "Invalid interval — only monthly billing is supported at launch"}, event)

		price_id = _get_price_id(plan, interval)

		sub = get_subscription(user_id)
		customer_id = sub.get("stripe_customer_id")

		if not customer_id:
			customer = stripe.Customer.create(metadata={"user_id": user_id})
			customer_id = customer.id

		cors_origins = list(_CORS_ALLOWED_ORIGINS)
		base_url = cors_origins[0] if cors_origins else "http://localhost:3001"

		session_kwargs = {
			"customer": customer_id,
			"mode": "subscription",
			"line_items": [{"price": price_id, "quantity": 1}],
			"success_url": f"{base_url}/dashboard?checkout=success",
			"cancel_url": f"{base_url}/onboarding/checkout?cancelled=1",
			"client_reference_id": user_id,
			"metadata": {"user_id": user_id, "plan": plan},
		}

		if is_trial:
			session_kwargs["subscription_data"] = {"trial_period_days": 14}
			session_kwargs["payment_method_collection"] = "always"

		session = stripe.checkout.Session.create(**session_kwargs)

		logger.info("Checkout session created",
					 user_id=user_id, plan=plan, interval=interval, is_trial=is_trial)
		return _response(200, {"checkout_url": session.url}, event)

	except ValueError as e:
		return _response(400, {"message": str(e)}, event)
	except Exception as e:
		logger.error("Failed to create checkout session", error=e, user_id=user_id)
		return _response(500, {"message": "Failed to create checkout session"}, event)


# ─── Customer Portal ──────────────────────────────────────────────────────────

def create_customer_portal_handler(event, context):
	"""POST /billing/portal — Create a Stripe Customer Portal Session."""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err

	user_id = user_data["sub"]

	try:
		sub = get_subscription(user_id)
		customer_id = sub.get("stripe_customer_id")

		if not customer_id:
			return _response(400, {
				"message": "No billing account found. Subscribe to a plan first."
			}, event)

		cors_origins = list(_CORS_ALLOWED_ORIGINS)
		base_url = cors_origins[0] if cors_origins else "http://localhost:3001"

		# Use SnowScrape-specific portal configuration if set so we don't
		# fall through to the LLC-shared default (which is owned by SnowFort).
		session_kwargs = {
			"customer": customer_id,
			"return_url": f"{base_url}/dashboard/settings?tab=billing",
		}
		portal_config_id = os.environ.get("STRIPE_PORTAL_CONFIG_ID", "")
		if portal_config_id:
			session_kwargs["configuration"] = portal_config_id

		session = stripe.billing_portal.Session.create(**session_kwargs)

		logger.info("Portal session created", user_id=user_id)
		return _response(200, {"portal_url": session.url}, event)

	except Exception as e:
		logger.error("Failed to create portal session", error=e, user_id=user_id)
		return _response(500, {"message": "Failed to create portal session"}, event)


# ─── Stripe Webhook ───────────────────────────────────────────────────────────

def stripe_webhook_handler(event, context):
	"""
	POST /billing/webhook — Idempotent Stripe webhook receiver.
	1. Verify signature (400 on failure).
	2. Conditional-put on event_id to dedup; duplicate → 200 immediately.
	3. Dispatch handler. On exception → roll back dedup row and return 500
	   so Stripe retries.
	"""
	log_lambda_invocation(event, context, logger)

	webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
	if not webhook_secret:
		logger.error("STRIPE_WEBHOOK_SECRET not configured")
		return {"statusCode": 500, "body": "Webhook secret not configured"}

	body = event.get("body", "")
	if event.get("isBase64Encoded"):
		import base64
		body = base64.b64decode(body).decode("utf-8")

	sig_header = (event.get("headers", {}) or {}).get("stripe-signature", "")

	try:
		stripe_event = stripe.Webhook.construct_event(body, sig_header, webhook_secret)
	except stripe.SignatureVerificationError:
		logger.warning("Invalid Stripe webhook signature")
		return {"statusCode": 400, "body": "Invalid signature"}
	except Exception as e:
		logger.error("Webhook verification failed", error=e)
		return {"statusCode": 400, "body": "Webhook verification failed"}

	event_id = stripe_event["id"]
	event_type = stripe_event["type"]

	# Idempotency: conditional put on event_id.
	dedup_table = _get_dedup_table()
	ttl_epoch = int((datetime.now(timezone.utc) + timedelta(days=_DEDUP_TTL_DAYS)).timestamp())
	try:
		dedup_table.put_item(
			Item={"event_id": event_id, "ttl": ttl_epoch, "type": event_type},
			ConditionExpression="attribute_not_exists(event_id)",
		)
	except ClientError as e:
		if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
			logger.info("Duplicate webhook ignored", event_id=event_id, type=event_type)
			return {"statusCode": 200, "body": "Already processed"}
		logger.error("Dedup put_item failed", error=e, event_id=event_id)
		return {"statusCode": 500, "body": "Dedup failed"}

	logger.info("Stripe webhook received", event_id=event_id, event_type=event_type)
	data = stripe_event["data"]["object"]

	try:
		_dispatch_event(event_type, data)
	except Exception as e:
		logger.error("Webhook handler failed", error=e,
					 event_id=event_id, event_type=event_type)
		# Roll back dedup so Stripe retries
		try:
			dedup_table.delete_item(Key={"event_id": event_id})
		except Exception as rollback_err:
			logger.error("Failed to roll back dedup row", error=rollback_err,
						 event_id=event_id)
		return {"statusCode": 500, "body": "Processing failed"}

	return {"statusCode": 200, "body": "OK"}


def _dispatch_event(event_type: str, data: dict) -> None:
	"""Route a verified Stripe event to its handler."""
	if event_type == "checkout.session.completed":
		_handle_checkout_completed(data)
	elif event_type == "customer.subscription.updated":
		_handle_subscription_updated(data)
	elif event_type == "customer.subscription.deleted":
		_handle_subscription_deleted(data)
	elif event_type == "invoice.payment_succeeded":
		_handle_invoice_paid(data)
	elif event_type == "invoice.payment_failed":
		_handle_invoice_failed(data)
	else:
		logger.info("Unhandled webhook event", event_type=event_type)


def _handle_checkout_completed(session):
	"""Handle checkout.session.completed — new subscription created."""
	user_id = session.get("client_reference_id") or session.get("metadata", {}).get("user_id")
	customer_id = session.get("customer")
	subscription_id = session.get("subscription")
	plan = session.get("metadata", {}).get("plan", "pro")

	if not user_id:
		logger.error("Checkout completed but no user_id found", session_id=session.get("id"))
		return

	stripe_sub = stripe.Subscription.retrieve(subscription_id)

	trial_end_iso = (
		datetime.fromtimestamp(stripe_sub["trial_end"] or 0, tz=timezone.utc).isoformat()
		if stripe_sub.get("trial_end") else ""
	)
	period_end_iso = datetime.fromtimestamp(
		stripe_sub["current_period_end"], tz=timezone.utc
	).isoformat()

	create_or_update_subscription(
		user_id,
		plan=plan,
		status=stripe_sub["status"],
		stripe_customer_id=customer_id,
		stripe_subscription_id=subscription_id,
		current_period_start=datetime.fromtimestamp(
			stripe_sub["current_period_start"], tz=timezone.utc
		).isoformat(),
		current_period_end=period_end_iso,
		trial_end=trial_end_iso,
		cancel_at_period_end=bool(stripe_sub.get("cancel_at_period_end", False)),
		usage_reset_date=period_end_iso,
		monthly_pages_used=0,
	)

	logger.info("Subscription created via checkout",
				user_id=user_id, plan=plan, subscription_id=subscription_id,
				trial_end=trial_end_iso)


def _handle_subscription_updated(subscription):
	"""Handle customer.subscription.updated — plan/status/trial/cancel-at-period-end."""
	customer_id = subscription.get("customer")
	subscription_id = subscription.get("id")

	user_id = _find_user_by_customer_id(customer_id)
	if not user_id:
		logger.warning("Subscription updated for unknown customer", customer_id=customer_id)
		return

	plan = _plan_from_subscription(subscription)
	new_period_end_epoch = subscription["current_period_end"]
	new_period_end = datetime.fromtimestamp(new_period_end_epoch, tz=timezone.utc).isoformat()
	new_period_start = datetime.fromtimestamp(
		subscription["current_period_start"], tz=timezone.utc
	).isoformat()

	# Race fix: only shift usage_reset_date if the period boundary actually moved.
	# Normalize both to UTC epoch for comparison to avoid Z vs +00:00 mismatch.
	current_sub = get_subscription(user_id)
	stored_period_end_str = current_sub.get("current_period_end", "")
	try:
		stored_epoch = int(datetime.fromisoformat(
			stored_period_end_str.replace("Z", "+00:00")
		).timestamp()) if stored_period_end_str else 0
	except (ValueError, AttributeError):
		stored_epoch = 0
	period_moved = (stored_epoch != new_period_end_epoch)
	usage_reset_date = (
		new_period_end if period_moved
		else current_sub.get("usage_reset_date", new_period_end)
	)

	trial_end_epoch = subscription.get("trial_end")
	trial_end_iso = (
		datetime.fromtimestamp(trial_end_epoch, tz=timezone.utc).isoformat()
		if trial_end_epoch else ""
	)

	create_or_update_subscription(
		user_id,
		plan=plan,
		status=subscription.get("status", "active"),
		stripe_customer_id=customer_id,
		stripe_subscription_id=subscription_id,
		current_period_start=new_period_start,
		current_period_end=new_period_end,
		trial_end=trial_end_iso,
		cancel_at_period_end=bool(subscription.get("cancel_at_period_end", False)),
		usage_reset_date=usage_reset_date,
		monthly_pages_used=int(current_sub.get("monthly_pages_used", 0)),
	)

	logger.info("Subscription updated",
				user_id=user_id, plan=plan, status=subscription.get("status"))


def _handle_subscription_deleted(subscription):
	"""Handle customer.subscription.deleted — set plan to locked, status canceled."""
	customer_id = subscription.get("customer")
	user_id = _find_user_by_customer_id(customer_id)
	if not user_id:
		logger.warning("Subscription deleted for unknown customer", customer_id=customer_id)
		return

	create_or_update_subscription(
		user_id,
		plan="locked",
		status="canceled",
		stripe_customer_id=customer_id,
		stripe_subscription_id="",
	)

	logger.info("Subscription canceled, locked", user_id=user_id)


def _handle_invoice_paid(invoice):
	"""Handle invoice.payment_succeeded — reset usage for new period."""
	customer_id = invoice.get("customer")
	user_id = _find_user_by_customer_id(customer_id)
	if not user_id:
		return

	# Reset monthly usage
	try:
		table = get_table(os.environ.get("DYNAMODB_SUBSCRIPTIONS_TABLE", ""))
		table.update_item(
			Key={"user_id": user_id},
			UpdateExpression="SET monthly_pages_used = :zero, updated_at = :now",
			ExpressionAttributeValues={
				":zero": 0,
				":now": datetime.now(timezone.utc).isoformat(),
			},
		)
		logger.info("Usage reset on invoice payment", user_id=user_id)
	except Exception as e:
		logger.error("Failed to reset usage on invoice payment", error=e, user_id=user_id)


def _handle_invoice_failed(invoice):
	"""Handle invoice.payment_failed — mark subscription as past_due."""
	customer_id = invoice.get("customer")
	user_id = _find_user_by_customer_id(customer_id)
	if not user_id:
		return

	try:
		table = get_table(os.environ.get("DYNAMODB_SUBSCRIPTIONS_TABLE", ""))
		table.update_item(
			Key={"user_id": user_id},
			UpdateExpression="SET #s = :status, updated_at = :now",
			ExpressionAttributeNames={"#s": "status"},
			ExpressionAttributeValues={
				":status": "past_due",
				":now": datetime.now(timezone.utc).isoformat(),
			},
		)
		logger.info("Subscription marked past_due", user_id=user_id)
	except Exception as e:
		logger.error("Failed to update subscription status", error=e, user_id=user_id)


def _find_user_by_customer_id(customer_id: str) -> str | None:
	"""Look up user_id from stripe_customer_id via GSI."""
	if not customer_id:
		return None
	try:
		table = get_table(os.environ.get("DYNAMODB_SUBSCRIPTIONS_TABLE", ""))
		response = table.query(
			IndexName="StripeCustomerIndex",
			KeyConditionExpression="stripe_customer_id = :cid",
			ExpressionAttributeValues={":cid": customer_id},
			Limit=1,
		)
		items = response.get("Items", [])
		return items[0]["user_id"] if items else None
	except Exception as e:
		logger.error("Failed to look up user by customer_id",
					 error=e, customer_id=customer_id)
		return None


def _plan_from_subscription(subscription) -> str:
	"""Determine plan name from Stripe subscription's price metadata."""
	try:
		items = subscription.get("items", {}).get("data", [])
		if items:
			price = items[0].get("price", {})
			tier = price.get("metadata", {}).get("tier")
			if tier and tier in PLAN_LIMITS:
				return tier
	except Exception:
		pass
	return "pro"  # default if metadata not found


# ─── Subscription & Usage Queries ─────────────────────────────────────────────

def get_subscription_handler(event, context):
	"""GET /billing/subscription — Get current user's subscription."""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err

	user_id = user_data["sub"]
	sub = get_subscription(user_id)
	plan = sub.get("plan", "locked")
	limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["locked"])

	result = {
		"plan": plan,
		"status": sub.get("status", "no_subscription"),
		"current_period_end": sub.get("current_period_end", ""),
		"trial_end": sub.get("trial_end", ""),
		"cancel_at_period_end": bool(sub.get("cancel_at_period_end", False)),
		"monthly_page_limit": sub.get("monthly_page_limit", limits["monthly_pages"]),
		"monthly_pages_used": int(sub.get("monthly_pages_used", 0)),
		"concurrent_job_limit": sub.get("concurrent_job_limit", limits["concurrent_jobs"]),
		"features": sub.get("features", {
			"js_rendering": limits["js_rendering"],
			"proxy_rotation": limits["proxy_rotation"],
			"webhooks": limits["webhooks"],
			"anti_bot": limits["anti_bot"],
		}),
		"has_billing_account": bool(sub.get("stripe_customer_id")),
	}

	return _response(200, result, event)


def get_usage_handler(event, context):
	"""GET /billing/usage — Get current usage data."""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err

	user_id = user_data["sub"]
	sub = get_subscription(user_id)
	plan = sub.get("plan", "locked")
	limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["locked"])

	pages_used = int(sub.get("monthly_pages_used", 0))
	pages_limit = sub.get("monthly_page_limit", limits["monthly_pages"])

	if pages_limit == -1:
		pages_percentage = 0
	elif pages_limit > 0:
		pages_percentage = round((pages_used / pages_limit) * 100, 1)
	else:
		pages_percentage = 0

	result = {
		"pages_used": pages_used,
		"pages_limit": pages_limit,
		"pages_percentage": pages_percentage,
		"concurrent_job_limit": sub.get("concurrent_job_limit", limits["concurrent_jobs"]),
		"billing_period_end": sub.get("current_period_end", ""),
		"plan": plan,
	}

	return _response(200, result, event)


# ─── Usage Reset Cron ─────────────────────────────────────────────────────────

def reset_usage_cron_handler(event, context):
	"""Daily cron: reset usage for subscriptions past their reset date."""
	log_lambda_invocation(event, context, logger)

	reset_count = reset_all_expired_usage()
	logger.info("Usage reset cron completed", reset_count=reset_count)

	return {"statusCode": 200, "body": json.dumps({"reset_count": reset_count})}

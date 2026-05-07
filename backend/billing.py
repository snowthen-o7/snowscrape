"""
Plan definitions, usage tracking, and quota enforcement for SnowScrape billing.
Shared module imported by billing_handler.py and handler.py.
"""

import os
from datetime import datetime, timezone
from decimal import Decimal

from connection_pool import get_table
from logger import get_logger

logger = get_logger(__name__)

# ─── Plan Definitions ────────────────────────────────────────────────────────

PLAN_LIMITS = {
	"pro": {
		"monthly_pages": 25000,
		"concurrent_jobs": 5,
		"js_rendering": True,
		"proxy_rotation": True,
		"webhooks": True,
		"anti_bot": False,
	},
	"business": {
		"monthly_pages": 100000,
		"concurrent_jobs": 20,
		"js_rendering": True,
		"proxy_rotation": True,
		"webhooks": True,
		"anti_bot": True,
	},
	"enterprise": {
		"monthly_pages": -1,  # unlimited
		"concurrent_jobs": -1,  # unlimited
		"js_rendering": True,
		"proxy_rotation": True,
		"webhooks": True,
		"anti_bot": True,
	},
	"locked": {
		"monthly_pages": 0,
		"concurrent_jobs": 0,
		"js_rendering": False,
		"proxy_rotation": False,
		"webhooks": False,
		"anti_bot": False,
	},
}

# Synthetic status for users without any Stripe subscription.
NO_SUBSCRIPTION_STATUS = "no_subscription"

# Stripe statuses we treat as "billing is current, app access allowed".
ACTIVE_STATUSES = frozenset({"trialing", "active"})


def _get_subscriptions_table():
	table_name = os.environ.get('DYNAMODB_SUBSCRIPTIONS_TABLE', '')
	if not table_name:
		raise RuntimeError("DYNAMODB_SUBSCRIPTIONS_TABLE not configured")
	return get_table(table_name)


def _get_jobs_table():
	table_name = os.environ.get('DYNAMODB_JOBS_TABLE', '')
	if not table_name:
		raise RuntimeError("DYNAMODB_JOBS_TABLE not configured")
	return get_table(table_name)


# ─── Status Guard ────────────────────────────────────────────────────────────

def is_subscription_active(subscription: dict) -> bool:
	"""
	Return True if the subscription is in a state that allows app access.

	Trialing and active are the only happy paths. Past_due, canceled,
	incomplete, and the synthetic no_subscription all return False.
	"""
	status = (subscription or {}).get("status", "")
	return status in ACTIVE_STATUSES


# ─── Subscription Management ─────────────────────────────────────────────────

def get_subscription(user_id: str) -> dict:
	"""
	Fetch subscription for a user. Returns locked sentinel if none exists.
	"""
	try:
		table = _get_subscriptions_table()
		response = table.get_item(Key={"user_id": user_id})
		item = response.get("Item")

		if not item:
			return _default_subscription(user_id)

		_reset_usage_if_needed(item)
		return item
	except Exception as e:
		logger.warning("Failed to fetch subscription, returning locked sentinel",
					   user_id=user_id, error=str(e))
		return _default_subscription(user_id)


def _default_subscription(user_id: str) -> dict:
	"""Return a locked sentinel for users with no Stripe subscription."""
	limits = PLAN_LIMITS["locked"]
	return {
		"user_id": user_id,
		"plan": "locked",
		"status": NO_SUBSCRIPTION_STATUS,
		"monthly_page_limit": limits["monthly_pages"],
		"monthly_pages_used": 0,
		"concurrent_job_limit": limits["concurrent_jobs"],
		"trial_end": "",
		"cancel_at_period_end": False,
		"features": {
			"js_rendering": limits["js_rendering"],
			"proxy_rotation": limits["proxy_rotation"],
			"webhooks": limits["webhooks"],
			"anti_bot": limits["anti_bot"],
		},
	}


def create_or_update_subscription(user_id: str, **kwargs) -> dict:
	"""
	Create or update a subscription row in DynamoDB. Persists trial_end
	and cancel_at_period_end when supplied.
	"""
	table = _get_subscriptions_table()
	now = datetime.now(timezone.utc).isoformat()

	plan = kwargs.get("plan", "locked")
	if plan not in PLAN_LIMITS:
		raise ValueError(f"Unknown plan: {plan}")
	limits = PLAN_LIMITS[plan]

	item = {
		"user_id": user_id,
		"plan": plan,
		"status": kwargs.get("status", "active"),
		"stripe_customer_id": kwargs.get("stripe_customer_id", ""),
		"stripe_subscription_id": kwargs.get("stripe_subscription_id", ""),
		"current_period_start": kwargs.get("current_period_start", now),
		"current_period_end": kwargs.get("current_period_end", ""),
		"trial_end": kwargs.get("trial_end", ""),
		"cancel_at_period_end": bool(kwargs.get("cancel_at_period_end", False)),
		"monthly_page_limit": limits["monthly_pages"],
		"monthly_pages_used": kwargs.get("monthly_pages_used", 0),
		"concurrent_job_limit": limits["concurrent_jobs"],
		"usage_reset_date": kwargs.get("usage_reset_date", ""),
		"features": {
			"js_rendering": limits["js_rendering"],
			"proxy_rotation": limits["proxy_rotation"],
			"webhooks": limits["webhooks"],
			"anti_bot": limits["anti_bot"],
		},
		"created_at": kwargs.get("created_at", now),
		"updated_at": now,
	}

	table.put_item(Item=item)
	logger.info("Subscription updated", user_id=user_id, plan=plan, status=item["status"])
	return item


# ─── Usage Enforcement ────────────────────────────────────────────────────────

def check_usage_quota(user_id: str, pages_requested: int = 1) -> dict:
	"""
	Check if a user has remaining page quota AND is on an active billing status.

	Returns:
		{allowed, plan, status, used, limit, remaining, reason?}
	"""
	sub = get_subscription(user_id)
	plan = sub.get("plan", "locked")
	status = sub.get("status", NO_SUBSCRIPTION_STATUS)

	if not is_subscription_active(sub):
		return {
			"allowed": False,
			"plan": plan,
			"status": status,
			"used": int(sub.get("monthly_pages_used", 0)),
			"limit": int(sub.get("monthly_page_limit", 0)),
			"remaining": 0,
			"reason": "subscription_inactive",
		}

	limit = sub.get("monthly_page_limit", PLAN_LIMITS[plan]["monthly_pages"])
	used = int(sub.get("monthly_pages_used", 0))

	if limit == -1:
		return {"allowed": True, "plan": plan, "status": status,
				"used": used, "limit": -1, "remaining": -1}

	remaining = max(0, limit - used)
	return {
		"allowed": remaining >= pages_requested,
		"plan": plan,
		"status": status,
		"used": used,
		"limit": limit,
		"remaining": remaining,
		"reason": None if remaining >= pages_requested else "quota_exceeded",
	}


def increment_usage(user_id: str, pages_count: int = 1) -> None:
	"""
	Atomically increment the monthly page usage counter. Fail-open.
	"""
	try:
		table = _get_subscriptions_table()
		table.update_item(
			Key={"user_id": user_id},
			UpdateExpression="ADD monthly_pages_used :count SET updated_at = :now",
			ExpressionAttributeValues={
				":count": pages_count,
				":now": datetime.now(timezone.utc).isoformat(),
			},
		)
	except Exception as e:
		logger.error("Failed to increment usage", error=e,
					 user_id=user_id, pages_count=pages_count)


def check_feature_access(user_id: str, feature_name: str) -> dict:
	"""
	Check if user's plan includes feature AND subscription is active.
	"""
	sub = get_subscription(user_id)
	plan = sub.get("plan", "locked")
	status = sub.get("status", NO_SUBSCRIPTION_STATUS)

	if not is_subscription_active(sub):
		return {"allowed": False, "plan": plan, "status": status,
				"feature": feature_name, "reason": "subscription_inactive"}

	features = sub.get("features", PLAN_LIMITS[plan])
	return {
		"allowed": bool(features.get(feature_name, False)),
		"plan": plan,
		"status": status,
		"feature": feature_name,
		"reason": None if features.get(feature_name) else "feature_not_in_plan",
	}


def check_concurrent_job_limit(user_id: str) -> dict:
	"""
	Check if user can create another concurrent job AND subscription is active.
	"""
	sub = get_subscription(user_id)
	plan = sub.get("plan", "locked")
	status = sub.get("status", NO_SUBSCRIPTION_STATUS)

	if not is_subscription_active(sub):
		return {"allowed": False, "plan": plan, "status": status,
				"active_jobs": 0, "limit": 0, "reason": "subscription_inactive"}

	limit = sub.get("concurrent_job_limit", PLAN_LIMITS[plan]["concurrent_jobs"])
	if limit == -1:
		return {"allowed": True, "plan": plan, "status": status,
				"active_jobs": 0, "limit": -1}

	try:
		jobs_table = _get_jobs_table()
		response = jobs_table.scan(
			FilterExpression="user_id = :uid AND (jobStatus = :active OR jobStatus = :running)",
			ExpressionAttributeValues={
				":uid": user_id,
				":active": "active",
				":running": "running",
			},
			Select="COUNT",
		)
		active_jobs = response.get("Count", 0)
	except Exception as e:
		logger.warning("Failed to count active jobs, allowing request",
					   user_id=user_id, error=str(e))
		return {"allowed": True, "plan": plan, "status": status,
				"active_jobs": 0, "limit": limit}

	return {
		"allowed": active_jobs < limit,
		"plan": plan,
		"status": status,
		"active_jobs": active_jobs,
		"limit": limit,
		"reason": None if active_jobs < limit else "concurrent_limit",
	}


# ─── Usage Reset ──────────────────────────────────────────────────────────────

def _reset_usage_if_needed(subscription: dict) -> None:
	"""Reset usage counter inline if usage_reset_date has passed."""
	reset_date_str = subscription.get("usage_reset_date", "")
	if not reset_date_str:
		return

	try:
		reset_date = datetime.fromisoformat(reset_date_str.replace("Z", "+00:00"))
		now = datetime.now(timezone.utc)
		if now >= reset_date:
			table = _get_subscriptions_table()
			table.update_item(
				Key={"user_id": subscription["user_id"]},
				UpdateExpression="SET monthly_pages_used = :zero, updated_at = :now",
				ExpressionAttributeValues={
					":zero": 0,
					":now": now.isoformat(),
				},
			)
			subscription["monthly_pages_used"] = 0
			logger.info("Usage reset for user", user_id=subscription["user_id"])
	except Exception as e:
		logger.warning("Failed to check/reset usage",
					   user_id=subscription.get("user_id"), error=str(e))


def reset_all_expired_usage() -> int:
	"""Daily cron safety net: scan and reset expired usage counters."""
	table = _get_subscriptions_table()
	now = datetime.now(timezone.utc).isoformat()
	reset_count = 0

	def _do_resets(items):
		nonlocal reset_count
		for item in items:
			try:
				table.update_item(
					Key={"user_id": item["user_id"]},
					UpdateExpression="SET monthly_pages_used = :zero, updated_at = :now",
					ExpressionAttributeValues={":zero": 0, ":now": now},
				)
				reset_count += 1
			except Exception as e:
				logger.error("Failed to reset usage for user",
							 error=e, user_id=item.get("user_id"))

	try:
		response = table.scan(
			FilterExpression="usage_reset_date <= :now AND monthly_pages_used > :zero",
			ExpressionAttributeValues={":now": now, ":zero": 0},
		)
		_do_resets(response.get("Items", []))
		while "LastEvaluatedKey" in response:
			response = table.scan(
				FilterExpression="usage_reset_date <= :now AND monthly_pages_used > :zero",
				ExpressionAttributeValues={":now": now, ":zero": 0},
				ExclusiveStartKey=response["LastEvaluatedKey"],
			)
			_do_resets(response.get("Items", []))
	except Exception as e:
		logger.error("Failed to scan for usage resets", error=e)

	logger.info("Usage reset cron completed", reset_count=reset_count)
	return reset_count

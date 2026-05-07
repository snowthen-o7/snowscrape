# SnowScrape Billing MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the first paying user — ship a 14-day trial of Pro with card upfront, real Settings → Billing tab, idempotent Stripe webhooks, and a one-time-secret API-key UI.

**Architecture:** Trial-only entry: Clerk signup → middleware gate → mandatory Stripe Checkout for Pro at $49/mo (14-day trial) before any app access. Stripe Customer Portal handles all self-service plan changes. New `BillingWebhookDedup` DynamoDB table provides at-least-once-with-idempotency for Stripe webhooks. Settings page Billing + API Keys tabs read live data via TanStack Query.

**Tech Stack:**
- Backend: Python 3.12 on AWS Lambda (handler-style), boto3 + DynamoDB, `stripe>=8.0.0` SDK
- Infra: SST Ion v3 (`sst.config.ts`), 3 new tables (Subscriptions, ApiKeys, BillingWebhookDedup), Doppler `sf-snowscrape` for secrets
- Frontend: Next.js 16 App Router, Clerk auth, TanStack Query v5, Tailwind v4 + Radix UI
- Testing: pytest + moto for backend, Vitest for frontend, Playwright for redirect/modal flows

**Spec:** `docs/superpowers/specs/2026-05-06-snowscrape-billing-mvp-design.md`

**Prerequisites (must resolve before starting):**
1. **Webhook URL strategy.** Spec recommends Option A (auto-generated API Gateway URL, captured at deploy time). This plan assumes Option A. If you want a custom domain, add a separate task before Task P4.4 to configure `sst.aws.ApiGatewayV2` custom domain.
2. **Confirm Enterprise mailto.** Spec uses `alex@snowforge.dev` as placeholder. Verify or replace before Task F8.
3. **Doppler `sf-snowscrape` project + dev/prd configs already exist** (per memory). If `prd` config doesn't exist, create it via `doppler configs create prd --project sf-snowscrape` before Task O3.

---

## File Structure

### Backend (Python 3.12)
- **Modify** `backend/billing.py` — drop `starter`, add `locked`, add `is_subscription_active`, switch `_default_subscription` to sentinel, persist `trial_end` and `cancel_at_period_end`.
- **Modify** `backend/billing_handler.py` — restructure webhook for idempotency, fix reset-date race, change canceled to lock instead of starter, accept `is_trial` flag, populate trial fields.
- **Modify** `backend/handler.py` — add `read_only_when_locked` decorator and apply to GET allowlist; tighten existing billing-enforcement block to consult `is_subscription_active`.
- **Modify** `backend/conftest.py` — add Subscriptions, ApiKeys, BillingWebhookDedup tables; add STRIPE_* env vars; add subscription fixtures.
- **Create** `backend/tests/unit/test_billing.py` — unit tests for `billing.py`.
- **Create** `backend/tests/unit/test_billing_handler.py` — unit tests for handler functions (mock Stripe).
- **Create** `backend/tests/integration/test_billing_flow.py` — integration tests for webhook idempotency and full flows.
- **Create** `backend/tests/fixtures/stripe_events/` — JSON fixtures for Stripe webhook payloads.

### Infrastructure (TypeScript)
- **Modify** `sst.config.ts` — add `BillingWebhookDedup` Dynamo table, remove unused `STRIPE_PRICE_STARTER_MONTHLY` / `STRIPE_PRICE_PRO_ANNUAL` / `STRIPE_PRICE_BUSINESS_ANNUAL` from `sharedEnv`, add new table to `allTables`.
- **Auto-regenerated** `sst.pyi` and `backend/sst.pyi` after `sst dev`/`sst deploy`.

### Frontend (TypeScript / Next.js 16)
- **Create** `frontend/lib/api/billing.ts` — `billingAPI` class with `getSubscription`, `getUsage`, `createCheckoutSession`, `createPortalSession` methods.
- **Create** `frontend/lib/api/api-keys.ts` — `apiKeysAPI` class with `list`, `create`, `delete`.
- **Modify** `frontend/lib/api/index.ts` — export new APIs.
- **Create** `frontend/lib/hooks/useSubscription.ts` — `useSubscription`, `useUsage`, `useStartCheckout`, `useOpenPortal` hooks.
- **Create** `frontend/lib/hooks/useApiKeys.ts` — `useApiKeys`, `useCreateApiKey`, `useDeleteApiKey` hooks.
- **Modify** `frontend/lib/hooks/index.ts` — export new hooks.
- **Create** `frontend/middleware.ts` — Clerk auth + subscription-status gate.
- **Create** `frontend/app/(application)/onboarding/checkout/page.tsx` — Pre-checkout landing page.
- **Create** `frontend/app/(application)/billing/locked/page.tsx` — Locked-account screen.
- **Modify** `frontend/app/(application)/dashboard/settings/page.tsx` — wire Billing and API Keys tabs to live data; new one-time-secret modal.
- **Create** `frontend/components/billing/CreateApiKeyDialog.tsx` — extracted modal component.
- **Modify** `frontend/app/(marketing)/pricing/page.tsx` — drop Starter card, update CTAs.
- **Create** `frontend/components/marketing/PricingCTA.tsx` — routing logic for pricing-card CTAs.
- **Create** `frontend/lib/__tests__/api/billing.test.ts` — Vitest unit tests for API client.
- **Create** `frontend/lib/__tests__/hooks/useSubscription.test.ts` — Vitest unit tests for hook.
- **Create** `frontend/e2e/billing-flow.spec.ts` — Playwright tests for redirects + modal.

### Docs
- **Modify** `docs/INFRASTRUCTURE.md` — document Subscriptions, ApiKeys, BillingWebhookDedup tables; document trial-only flow; update env vars section.
- **Modify** `PROGRESS.md` — mark Billing MVP done.
- **Modify** `backend/openapi.yml` — add 5 billing routes + 3 api-key routes.

---

## Phase B — Backend code (TDD)

### Task B1: Extend conftest.py with billing fixtures

**Files:**
- Modify: `backend/conftest.py`

- [ ] **Step 1: Add STRIPE_* env vars to `mock_env_vars` fixture**

In `backend/conftest.py`, locate the `mock_env_vars` fixture (around line 33) and append these lines inside the function body, before `yield`:

```python
	os.environ['DYNAMODB_SUBSCRIPTIONS_TABLE'] = 'SnowscrapeSubscriptions-test'
	os.environ['DYNAMODB_API_KEYS_TABLE'] = 'SnowscrapeApiKeys-test'
	os.environ['DYNAMODB_BILLING_WEBHOOK_DEDUP_TABLE'] = 'SnowscrapeBillingWebhookDedup-test'
	os.environ['STRIPE_SECRET_KEY'] = 'sk_test_dummy'
	os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test_dummy'
	os.environ['STRIPE_PRICE_PRO_MONTHLY'] = 'price_test_pro_monthly'
	os.environ['STRIPE_PRICE_BUSINESS_MONTHLY'] = 'price_test_business_monthly'
	os.environ['CORS_ALLOWED_ORIGIN'] = 'http://localhost:3001'
```

In the cleanup loop at the bottom of `mock_env_vars`, add the same key names to the list of keys to delete.

- [ ] **Step 2: Add table creation to `dynamodb_client` fixture**

In `backend/conftest.py`, locate the `dynamodb_client` fixture and add three new `create_table` calls after the existing `Webhook Deliveries table` block, before `yield dynamodb`:

```python
		# Subscriptions table
		dynamodb.create_table(
			TableName='SnowscrapeSubscriptions-test',
			KeySchema=[
				{'AttributeName': 'user_id', 'KeyType': 'HASH'}
			],
			AttributeDefinitions=[
				{'AttributeName': 'user_id', 'AttributeType': 'S'},
				{'AttributeName': 'stripe_customer_id', 'AttributeType': 'S'}
			],
			GlobalSecondaryIndexes=[
				{
					'IndexName': 'StripeCustomerIndex',
					'KeySchema': [
						{'AttributeName': 'stripe_customer_id', 'KeyType': 'HASH'}
					],
					'Projection': {'ProjectionType': 'ALL'}
				}
			],
			BillingMode='PAY_PER_REQUEST'
		)

		# ApiKeys table
		dynamodb.create_table(
			TableName='SnowscrapeApiKeys-test',
			KeySchema=[
				{'AttributeName': 'api_key_id', 'KeyType': 'HASH'}
			],
			AttributeDefinitions=[
				{'AttributeName': 'api_key_id', 'AttributeType': 'S'},
				{'AttributeName': 'user_id', 'AttributeType': 'S'},
				{'AttributeName': 'key_hash', 'AttributeType': 'S'}
			],
			GlobalSecondaryIndexes=[
				{
					'IndexName': 'UserIdIndex',
					'KeySchema': [
						{'AttributeName': 'user_id', 'KeyType': 'HASH'}
					],
					'Projection': {'ProjectionType': 'ALL'}
				},
				{
					'IndexName': 'KeyHashIndex',
					'KeySchema': [
						{'AttributeName': 'key_hash', 'KeyType': 'HASH'}
					],
					'Projection': {'ProjectionType': 'ALL'}
				}
			],
			BillingMode='PAY_PER_REQUEST'
		)

		# BillingWebhookDedup table
		dynamodb.create_table(
			TableName='SnowscrapeBillingWebhookDedup-test',
			KeySchema=[
				{'AttributeName': 'event_id', 'KeyType': 'HASH'}
			],
			AttributeDefinitions=[
				{'AttributeName': 'event_id', 'AttributeType': 'S'}
			],
			BillingMode='PAY_PER_REQUEST'
		)
```

- [ ] **Step 3: Add subscription sample fixtures**

At the end of `backend/conftest.py`, add:

```python
@pytest.fixture
def sample_pro_trialing_subscription():
	"""Subscription row for a user mid-trial."""
	now = datetime.now(timezone.utc)
	return {
		'user_id': 'user-trial-1',
		'plan': 'pro',
		'status': 'trialing',
		'stripe_customer_id': 'cus_test_trial1',
		'stripe_subscription_id': 'sub_test_trial1',
		'current_period_start': now.isoformat(),
		'current_period_end': (now.replace(microsecond=0)).isoformat(),
		'trial_end': (now.replace(microsecond=0)).isoformat(),
		'cancel_at_period_end': False,
		'monthly_page_limit': 25000,
		'monthly_pages_used': 0,
		'concurrent_job_limit': 5,
		'usage_reset_date': (now.replace(microsecond=0)).isoformat(),
		'features': {
			'js_rendering': True,
			'proxy_rotation': True,
			'webhooks': True,
			'anti_bot': False,
		},
		'created_at': now.isoformat(),
		'updated_at': now.isoformat(),
	}


@pytest.fixture
def sample_pro_active_subscription(sample_pro_trialing_subscription):
	"""Subscription row for a user past trial, paying."""
	sub = dict(sample_pro_trialing_subscription)
	sub['status'] = 'active'
	sub['user_id'] = 'user-active-1'
	sub['stripe_customer_id'] = 'cus_test_active1'
	sub['stripe_subscription_id'] = 'sub_test_active1'
	sub['trial_end'] = ''
	return sub
```

- [ ] **Step 4: Run existing tests to confirm no regressions**

```
cd backend
uv run pytest tests/ -v
```

Expected: all existing tests still pass (the new env vars are additive; new tables are unused so far).

- [ ] **Step 5: Commit**

```
git add backend/conftest.py
git commit -m "test: extend backend conftest with billing fixtures + tables"
```

---

### Task B2: Refactor billing.py — drop starter, add locked, status guard

**Files:**
- Modify: `backend/billing.py`
- Test: `backend/tests/unit/test_billing.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_billing.py`:

```python
"""Unit tests for billing.py — plan limits, status guards, default sentinel."""
import pytest
from unittest.mock import patch


@pytest.mark.unit
class TestPlanLimits:
	def test_pro_plan_exists_with_25000_pages(self, mock_env_vars):
		from billing import PLAN_LIMITS
		assert PLAN_LIMITS['pro']['monthly_pages'] == 25000
		assert PLAN_LIMITS['pro']['concurrent_jobs'] == 5
		assert PLAN_LIMITS['pro']['js_rendering'] is True
		assert PLAN_LIMITS['pro']['proxy_rotation'] is True
		assert PLAN_LIMITS['pro']['webhooks'] is True
		assert PLAN_LIMITS['pro']['anti_bot'] is False

	def test_business_plan_includes_anti_bot(self, mock_env_vars):
		from billing import PLAN_LIMITS
		assert PLAN_LIMITS['business']['monthly_pages'] == 100000
		assert PLAN_LIMITS['business']['anti_bot'] is True

	def test_enterprise_plan_unlimited(self, mock_env_vars):
		from billing import PLAN_LIMITS
		assert PLAN_LIMITS['enterprise']['monthly_pages'] == -1
		assert PLAN_LIMITS['enterprise']['concurrent_jobs'] == -1

	def test_locked_plan_zero_everything(self, mock_env_vars):
		from billing import PLAN_LIMITS
		assert PLAN_LIMITS['locked']['monthly_pages'] == 0
		assert PLAN_LIMITS['locked']['concurrent_jobs'] == 0
		assert PLAN_LIMITS['locked']['js_rendering'] is False
		assert PLAN_LIMITS['locked']['proxy_rotation'] is False
		assert PLAN_LIMITS['locked']['webhooks'] is False
		assert PLAN_LIMITS['locked']['anti_bot'] is False

	def test_starter_plan_removed(self, mock_env_vars):
		from billing import PLAN_LIMITS
		assert 'starter' not in PLAN_LIMITS


@pytest.mark.unit
class TestIsSubscriptionActive:
	def test_trialing_is_active(self, mock_env_vars):
		from billing import is_subscription_active
		assert is_subscription_active({'status': 'trialing'}) is True

	def test_active_is_active(self, mock_env_vars):
		from billing import is_subscription_active
		assert is_subscription_active({'status': 'active'}) is True

	def test_past_due_is_inactive(self, mock_env_vars):
		from billing import is_subscription_active
		assert is_subscription_active({'status': 'past_due'}) is False

	def test_canceled_is_inactive(self, mock_env_vars):
		from billing import is_subscription_active
		assert is_subscription_active({'status': 'canceled'}) is False

	def test_no_subscription_is_inactive(self, mock_env_vars):
		from billing import is_subscription_active
		assert is_subscription_active({'status': 'no_subscription'}) is False

	def test_incomplete_is_inactive(self, mock_env_vars):
		from billing import is_subscription_active
		assert is_subscription_active({'status': 'incomplete'}) is False

	def test_missing_status_is_inactive(self, mock_env_vars):
		from billing import is_subscription_active
		assert is_subscription_active({}) is False


@pytest.mark.unit
class TestDefaultSubscription:
	def test_default_returns_locked_sentinel(self, mock_env_vars):
		from billing import _default_subscription
		sub = _default_subscription('user-x')
		assert sub['user_id'] == 'user-x'
		assert sub['plan'] == 'locked'
		assert sub['status'] == 'no_subscription'
		assert sub['monthly_page_limit'] == 0


@pytest.mark.unit
@pytest.mark.aws
class TestQuotaChecks:
	def test_quota_denied_when_status_inactive(self, dynamodb_client, mock_env_vars):
		from billing import check_usage_quota
		# No subscription row exists → returns sentinel → inactive → denied
		result = check_usage_quota('user-no-sub')
		assert result['allowed'] is False
		assert result['plan'] == 'locked'

	def test_quota_allowed_for_trialing_user(
		self, dynamodb_client, mock_env_vars, sample_pro_trialing_subscription
	):
		from billing import check_usage_quota
		dynamodb_client.Table('SnowscrapeSubscriptions-test').put_item(
			Item=sample_pro_trialing_subscription
		)
		result = check_usage_quota('user-trial-1')
		assert result['allowed'] is True
		assert result['plan'] == 'pro'
		assert result['remaining'] == 25000
```

- [ ] **Step 2: Run tests — expect failure**

```
cd backend
uv run pytest tests/unit/test_billing.py -v
```

Expected: most tests FAIL because `is_subscription_active` doesn't exist, `locked` plan isn't defined, `starter` is still defined.

- [ ] **Step 3: Update billing.py**

Replace the contents of `backend/billing.py` with:

```python
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
```

- [ ] **Step 4: Run tests — expect pass**

```
cd backend
uv run pytest tests/unit/test_billing.py -v
```

Expected: ALL tests in `test_billing.py` PASS.

- [ ] **Step 5: Run the full suite to confirm no regressions**

```
cd backend
uv run pytest tests/ -v
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```
git add backend/billing.py backend/tests/unit/test_billing.py
git commit -m "refactor(billing): drop starter, add locked sentinel, status guard"
```

---

### Task B3: Refactor billing_handler.py — webhook idempotency

**Files:**
- Modify: `backend/billing_handler.py`
- Test: `backend/tests/unit/test_billing_handler.py` (create)

- [ ] **Step 1: Write failing tests for idempotency**

Create `backend/tests/unit/test_billing_handler.py`:

```python
"""Unit tests for billing_handler.py — webhook idempotency, dispatch, edge cases."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def stripe_event_checkout_completed():
	return {
		"id": "evt_test_001",
		"type": "checkout.session.completed",
		"data": {
			"object": {
				"id": "cs_test_001",
				"client_reference_id": "user-cko-1",
				"customer": "cus_test_cko1",
				"subscription": "sub_test_cko1",
				"metadata": {"user_id": "user-cko-1", "plan": "pro"},
			}
		},
	}


@pytest.fixture
def stripe_subscription_object():
	"""Mock object returned by stripe.Subscription.retrieve."""
	sub = MagicMock()
	sub.status = "trialing"
	sub.current_period_start = 1700000000
	sub.current_period_end = 1701209600
	sub.trial_end = 1701209600
	sub.cancel_at_period_end = False
	sub.id = "sub_test_cko1"
	sub.customer = "cus_test_cko1"
	# items[0].price.metadata.tier
	price = MagicMock()
	price.metadata = {"tier": "pro"}
	item = MagicMock()
	item.price = price
	sub.__getitem__.side_effect = lambda k: {
		"items": {"data": [{"price": {"metadata": {"tier": "pro"}}}]},
		"current_period_start": 1700000000,
		"current_period_end": 1701209600,
		"status": "trialing",
		"id": "sub_test_cko1",
		"customer": "cus_test_cko1",
	}[k]
	return sub


@pytest.mark.unit
@pytest.mark.aws
class TestWebhookIdempotency:
	def test_first_event_id_writes_dedup_row_and_dispatches(
		self, dynamodb_client, mock_env_vars, stripe_event_checkout_completed,
		stripe_subscription_object, lambda_context
	):
		from billing_handler import stripe_webhook_handler
		event = {
			"body": json.dumps(stripe_event_checkout_completed),
			"headers": {"stripe-signature": "fake"},
			"isBase64Encoded": False,
		}
		with patch("billing_handler.stripe.Webhook.construct_event",
				   return_value=stripe_event_checkout_completed):
			with patch("billing_handler.stripe.Subscription.retrieve",
					   return_value=stripe_subscription_object):
				resp = stripe_webhook_handler(event, lambda_context)
		assert resp["statusCode"] == 200

		# dedup row exists
		dedup_table = dynamodb_client.Table('SnowscrapeBillingWebhookDedup-test')
		row = dedup_table.get_item(Key={"event_id": "evt_test_001"}).get("Item")
		assert row is not None
		assert row["event_id"] == "evt_test_001"

		# subscription row created
		subs_table = dynamodb_client.Table('SnowscrapeSubscriptions-test')
		sub = subs_table.get_item(Key={"user_id": "user-cko-1"}).get("Item")
		assert sub is not None
		assert sub["plan"] == "pro"
		assert sub["status"] == "trialing"

	def test_duplicate_event_id_returns_200_without_dispatch(
		self, dynamodb_client, mock_env_vars, stripe_event_checkout_completed,
		lambda_context
	):
		from billing_handler import stripe_webhook_handler
		# Pre-seed dedup table
		dedup_table = dynamodb_client.Table('SnowscrapeBillingWebhookDedup-test')
		dedup_table.put_item(Item={
			"event_id": "evt_test_001",
			"ttl": 9999999999,
			"type": "checkout.session.completed",
		})

		event = {
			"body": json.dumps(stripe_event_checkout_completed),
			"headers": {"stripe-signature": "fake"},
			"isBase64Encoded": False,
		}
		with patch("billing_handler.stripe.Webhook.construct_event",
				   return_value=stripe_event_checkout_completed):
			with patch("billing_handler.stripe.Subscription.retrieve") as mock_retrieve:
				resp = stripe_webhook_handler(event, lambda_context)
		assert resp["statusCode"] == 200
		# Dispatch was skipped (Subscription.retrieve never called)
		mock_retrieve.assert_not_called()

		# No subscription row created
		subs_table = dynamodb_client.Table('SnowscrapeSubscriptions-test')
		sub = subs_table.get_item(Key={"user_id": "user-cko-1"}).get("Item")
		assert sub is None

	def test_dispatch_failure_returns_500_and_rolls_back_dedup(
		self, dynamodb_client, mock_env_vars, stripe_event_checkout_completed,
		lambda_context
	):
		from billing_handler import stripe_webhook_handler
		event = {
			"body": json.dumps(stripe_event_checkout_completed),
			"headers": {"stripe-signature": "fake"},
			"isBase64Encoded": False,
		}
		with patch("billing_handler.stripe.Webhook.construct_event",
				   return_value=stripe_event_checkout_completed):
			with patch("billing_handler.stripe.Subscription.retrieve",
					   side_effect=Exception("simulated stripe failure")):
				resp = stripe_webhook_handler(event, lambda_context)
		assert resp["statusCode"] == 500

		# Dedup row was rolled back so Stripe retry can re-enter
		dedup_table = dynamodb_client.Table('SnowscrapeBillingWebhookDedup-test')
		row = dedup_table.get_item(Key={"event_id": "evt_test_001"}).get("Item")
		assert row is None

	def test_invalid_signature_returns_400(
		self, dynamodb_client, mock_env_vars, lambda_context
	):
		import stripe
		from billing_handler import stripe_webhook_handler
		event = {
			"body": "{}",
			"headers": {"stripe-signature": "bad"},
			"isBase64Encoded": False,
		}
		with patch("billing_handler.stripe.Webhook.construct_event",
				   side_effect=stripe.SignatureVerificationError("bad", "sig")):
			resp = stripe_webhook_handler(event, lambda_context)
		assert resp["statusCode"] == 400
```

- [ ] **Step 2: Run tests — expect failure**

```
cd backend
uv run pytest tests/unit/test_billing_handler.py -v
```

Expected: tests FAIL because the dedup logic doesn't exist yet.

- [ ] **Step 3: Update billing_handler.py — replace `stripe_webhook_handler`**

In `backend/billing_handler.py`, locate the `stripe_webhook_handler` function. Replace it (and add the new helper) with:

```python
from datetime import timedelta
from botocore.exceptions import ClientError


_DEDUP_TTL_DAYS = 30


def _get_dedup_table():
	table_name = os.environ.get("DYNAMODB_BILLING_WEBHOOK_DEDUP_TABLE", "")
	if not table_name:
		raise RuntimeError("DYNAMODB_BILLING_WEBHOOK_DEDUP_TABLE not configured")
	return get_table(table_name)


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
```

- [ ] **Step 4: Run tests — expect idempotency tests pass**

```
cd backend
uv run pytest tests/unit/test_billing_handler.py::TestWebhookIdempotency -v
```

Expected: all 4 tests in TestWebhookIdempotency PASS.

- [ ] **Step 5: Commit**

```
git add backend/billing_handler.py backend/tests/unit/test_billing_handler.py
git commit -m "feat(billing): idempotent Stripe webhook with retry-safe dispatch"
```

---

### Task B4: Update billing_handler.py — trial fields, race fix, canceled→locked

**Files:**
- Modify: `backend/billing_handler.py`
- Test: `backend/tests/unit/test_billing_handler.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/unit/test_billing_handler.py`:

```python
@pytest.mark.unit
@pytest.mark.aws
class TestCheckoutWithTrial:
	def test_create_checkout_passes_trial_period_when_is_trial_true(
		self, dynamodb_client, mock_env_vars, lambda_context
	):
		from billing_handler import create_checkout_session_handler
		mock_session = MagicMock()
		mock_session.url = "https://stripe.test/checkout"
		mock_customer = MagicMock()
		mock_customer.id = "cus_new_1"

		event = {
			"headers": {"Authorization": "Bearer t", "origin": "http://localhost:3001"},
			"body": json.dumps({"plan": "pro", "is_trial": True}),
		}
		with patch("billing_handler.validate_clerk_token",
				   return_value={"sub": "user-trial-x"}):
			with patch("billing_handler.stripe.Customer.create",
					   return_value=mock_customer):
				with patch("billing_handler.stripe.checkout.Session.create",
						   return_value=mock_session) as mock_create:
					resp = create_checkout_session_handler(event, lambda_context)

		assert resp["statusCode"] == 200
		_, kwargs = mock_create.call_args
		assert kwargs.get("subscription_data") == {"trial_period_days": 14}
		assert kwargs.get("payment_method_collection") == "always"

	def test_create_checkout_omits_trial_when_is_trial_false(
		self, dynamodb_client, mock_env_vars, lambda_context
	):
		from billing_handler import create_checkout_session_handler
		mock_session = MagicMock()
		mock_session.url = "https://stripe.test/checkout"
		mock_customer = MagicMock()
		mock_customer.id = "cus_new_2"

		event = {
			"headers": {"Authorization": "Bearer t", "origin": "http://localhost:3001"},
			"body": json.dumps({"plan": "pro", "is_trial": False}),
		}
		with patch("billing_handler.validate_clerk_token",
				   return_value={"sub": "user-no-trial-x"}):
			with patch("billing_handler.stripe.Customer.create",
					   return_value=mock_customer):
				with patch("billing_handler.stripe.checkout.Session.create",
						   return_value=mock_session) as mock_create:
					resp = create_checkout_session_handler(event, lambda_context)

		assert resp["statusCode"] == 200
		_, kwargs = mock_create.call_args
		assert kwargs.get("subscription_data") is None or "trial_period_days" not in (kwargs.get("subscription_data") or {})


@pytest.mark.unit
@pytest.mark.aws
class TestSubscriptionDeletedSetsLocked:
	def test_canceled_subscription_sets_plan_locked(
		self, dynamodb_client, mock_env_vars,
		sample_pro_active_subscription
	):
		from billing_handler import _handle_subscription_deleted
		# Seed an active subscription
		dynamodb_client.Table('SnowscrapeSubscriptions-test').put_item(
			Item=sample_pro_active_subscription
		)
		stripe_data = {"customer": "cus_test_active1", "id": "sub_test_active1"}
		_handle_subscription_deleted(stripe_data)

		row = dynamodb_client.Table('SnowscrapeSubscriptions-test').get_item(
			Key={"user_id": "user-active-1"}
		).get("Item")
		assert row["plan"] == "locked"
		assert row["status"] == "canceled"


@pytest.mark.unit
@pytest.mark.aws
class TestSubscriptionUpdatedRaceFix:
	def test_payment_method_change_does_not_shift_reset_date(
		self, dynamodb_client, mock_env_vars,
		sample_pro_active_subscription
	):
		from billing_handler import _handle_subscription_updated
		# Seed a row with a known reset date
		original_reset = sample_pro_active_subscription['usage_reset_date']
		original_period_end = sample_pro_active_subscription['current_period_end']
		dynamodb_client.Table('SnowscrapeSubscriptions-test').put_item(
			Item=sample_pro_active_subscription
		)
		# Stripe sends an update with the SAME current_period_end
		# (i.e. user changed payment method, not a renewal)
		import datetime as dt
		end_epoch = int(dt.datetime.fromisoformat(original_period_end).timestamp())
		stripe_data = {
			"id": "sub_test_active1",
			"customer": "cus_test_active1",
			"status": "active",
			"current_period_start": end_epoch - 86400 * 30,
			"current_period_end": end_epoch,
			"trial_end": None,
			"cancel_at_period_end": False,
			"items": {"data": [{"price": {"metadata": {"tier": "pro"}}}]},
		}
		_handle_subscription_updated(stripe_data)

		row = dynamodb_client.Table('SnowscrapeSubscriptions-test').get_item(
			Key={"user_id": "user-active-1"}
		).get("Item")
		# usage_reset_date should not have moved
		assert row['usage_reset_date'] == original_reset
```

- [ ] **Step 2: Run tests — expect failure**

```
cd backend
uv run pytest tests/unit/test_billing_handler.py::TestCheckoutWithTrial tests/unit/test_billing_handler.py::TestSubscriptionDeletedSetsLocked tests/unit/test_billing_handler.py::TestSubscriptionUpdatedRaceFix -v
```

Expected: tests FAIL.

- [ ] **Step 3: Update `create_checkout_session_handler` in billing_handler.py**

Locate `create_checkout_session_handler`. Replace the `session = stripe.checkout.Session.create(...)` block with:

```python
		body_data = json.loads(event.get("body") or "{}")
		plan = body_data.get("plan", "pro")
		interval = body_data.get("interval", "month")
		is_trial = bool(body_data.get("is_trial", False))

		if plan not in ("pro", "business"):
			return _response(400, {"message": "Invalid plan"}, event)
		if interval not in ("month", "year"):
			return _response(400, {"message": "Invalid interval"}, event)

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
```

Also, in the same function, remove the now-redundant `create_or_update_subscription(...)` call that was made after the `Customer.create` call — the row is created on `checkout.session.completed`, not on checkout-session creation. The `stripe_customer_id` will be set when the webhook fires.

- [ ] **Step 4: Update `_handle_subscription_deleted`**

Replace the function body with:

```python
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
```

- [ ] **Step 5: Update `_handle_subscription_updated` — race fix + trial fields**

Replace the function body with:

```python
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
	current_sub = get_subscription(user_id)
	stored_period_end = current_sub.get("current_period_end", "")
	usage_reset_date = (
		new_period_end if new_period_end != stored_period_end
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
```

- [ ] **Step 6: Update `_handle_checkout_completed` — populate trial fields**

Replace the function body with:

```python
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
```

Note: `stripe_sub["..."]` (subscript) instead of `.attr` lets the same code run against both real `Subscription` objects and dict fixtures in tests.

- [ ] **Step 7: Update `get_subscription_handler` to surface trial fields**

In `backend/billing_handler.py`, locate `get_subscription_handler`. Update the `result` dict to include the new fields:

```python
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
```

Also, in the same function, change the `limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])` line to `limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["locked"])` (since `starter` no longer exists).

- [ ] **Step 8: Remove starter from `_get_price_id` whitelist**

In `backend/billing_handler.py`, locate `_get_price_id`. Remove the starter and annual entries:

```python
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
```

- [ ] **Step 9: Update `_plan_from_subscription` default**

In `backend/billing_handler.py`, change the fallback `return "pro"  # default if metadata not found` to:

```python
	return "pro"  # default if metadata not found — pro is the only trial-eligible tier
```

(Comment update only; logic stays.)

- [ ] **Step 10: Run tests**

```
cd backend
uv run pytest tests/unit/test_billing_handler.py -v
```

Expected: ALL tests in `test_billing_handler.py` PASS.

- [ ] **Step 11: Commit**

```
git add backend/billing_handler.py backend/tests/unit/test_billing_handler.py
git commit -m "feat(billing): trial-period support, canceled→locked, race-safe period reset"
```

---

### Task B5: Add read_only_when_locked decorator + apply

**Files:**
- Modify: `backend/handler.py`
- Test: `backend/tests/integration/test_billing_flow.py` (create)

- [ ] **Step 1: Write failing test**

Create `backend/tests/integration/test_billing_flow.py`:

```python
"""Integration tests covering full billing-driven user flows."""
import json
import pytest
from unittest.mock import patch


@pytest.mark.integration
@pytest.mark.aws
class TestLockedUserAccess:
	def test_locked_user_cannot_create_job(
		self, dynamodb_client, mock_env_vars, lambda_context
	):
		from handler import create_job_handler
		event = {
			"headers": {"Authorization": "Bearer t"},
			"body": json.dumps({
				"name": "Test",
				"source": "https://example.com/u.csv",
				"file_mapping": {"delimiter": ",", "enclosure": '"', "escape": "\\", "url_column": 0},
				"queries": [{"name": "title", "type": "xpath", "query": "//title"}],
				"rate_limit": 5,
			}),
		}
		with patch("handler.validate_clerk_token", return_value={"sub": "user-locked"}):
			resp = create_job_handler(event, lambda_context)
		assert resp["statusCode"] == 402
		body = json.loads(resp["body"])
		assert body["plan"] == "locked"

	def test_locked_user_can_list_jobs(
		self, dynamodb_client, mock_env_vars, lambda_context
	):
		from handler import get_jobs_handler
		event = {"headers": {"Authorization": "Bearer t"}}
		with patch("handler.validate_clerk_token", return_value={"sub": "user-locked"}):
			resp = get_jobs_handler(event, lambda_context)
		# 200 with empty list — read access preserved for locked users
		assert resp["statusCode"] == 200
```

- [ ] **Step 2: Run tests — expect failure**

```
cd backend
uv run pytest tests/integration/test_billing_flow.py -v
```

Expected: `test_locked_user_cannot_create_job` may pass already (existing fail-open in handler), `test_locked_user_can_list_jobs` is informational — make sure it's 200.

- [ ] **Step 3: Tighten the existing billing block in `handler.py`**

In `backend/handler.py`, locate the billing-enforcement block in `create_job_handler` (the section labeled `# ── Billing enforcement (fail-open) ──────────────────────────`). Replace its `try`/`except ImportError` clause to consume the new `is_subscription_active` guard. Find:

```python
		# ── Billing enforcement (fail-open) ──────────────────────────
		try:
			from billing import check_usage_quota, check_concurrent_job_limit, check_feature_access

			# Check page quota
			quota = check_usage_quota(user_data["sub"])
```

Replace with:

```python
		# ── Billing enforcement (fail-CLOSED on inactive sub, fail-open on errors) ──
		try:
			from billing import (
				check_usage_quota, check_concurrent_job_limit,
				check_feature_access, is_subscription_active, get_subscription,
			)

			# Hard gate: subscription must be active/trialing
			sub = get_subscription(user_data["sub"])
			if not is_subscription_active(sub):
				return {
					"statusCode": 402,
					"body": json.dumps({
						"message": "Active subscription required",
						"plan": sub.get("plan", "locked"),
						"status": sub.get("status", "no_subscription"),
					}),
					"headers": {
						'Access-Control-Allow-Origin': get_cors_origin(event),
						"Content-Type": "application/json"
					}
				}

			quota = check_usage_quota(user_data["sub"])
```

Leave the rest of the block (concurrent job, feature gates, ImportError fallback) as-is.

- [ ] **Step 4: Run tests**

```
cd backend
uv run pytest tests/integration/test_billing_flow.py -v
```

Expected: `test_locked_user_cannot_create_job` PASSES with statusCode 402 and `plan=locked`.

- [ ] **Step 5: Commit**

```
git add backend/handler.py backend/tests/integration/test_billing_flow.py
git commit -m "feat(billing): hard 402 gate on inactive subscription at job-create"
```

---

## Phase I — Infrastructure

### Task I1: Add BillingWebhookDedup table; remove unused env vars

**Files:**
- Modify: `sst.config.ts`

- [ ] **Step 1: Add BillingWebhookDedup table after the ApiKeys table**

In `sst.config.ts`, locate the `apiKeysTable` definition (around line 192). Immediately after its closing brace and before the `// ─── SQS Queues ──` comment, add:

```typescript
    const billingWebhookDedupTable = new sst.aws.Dynamo("BillingWebhookDedup", {
      fields: {
        event_id: "string",
      },
      primaryIndex: { hashKey: "event_id" },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
          ttl: { attributeName: "ttl", enabled: true },
        },
      },
    });
```

- [ ] **Step 2: Add table to allTables and sharedEnv**

In `sst.config.ts`, locate `const allTables = [...]` (around line 367). Add `billingWebhookDedupTable` as the last item.

In `sharedEnv`, locate `DYNAMODB_API_KEYS_TABLE: apiKeysTable.name,` and add immediately after:

```typescript
      DYNAMODB_BILLING_WEBHOOK_DEDUP_TABLE: billingWebhookDedupTable.name,
```

- [ ] **Step 3: Remove unused Stripe env vars**

In `sst.config.ts`, locate the `// Stripe (from Doppler)` block in `sharedEnv`. Replace it with:

```typescript
      // Stripe (from Doppler)
      STRIPE_SECRET_KEY: process.env.STRIPE_SECRET_KEY ?? "",
      STRIPE_WEBHOOK_SECRET: process.env.STRIPE_WEBHOOK_SECRET ?? "",
      STRIPE_PRICE_PRO_MONTHLY: process.env.STRIPE_PRICE_PRO_MONTHLY ?? "",
      STRIPE_PRICE_BUSINESS_MONTHLY: process.env.STRIPE_PRICE_BUSINESS_MONTHLY ?? "",
```

(Removes `STRIPE_PRICE_STARTER_MONTHLY`, `STRIPE_PRICE_PRO_ANNUAL`, `STRIPE_PRICE_BUSINESS_ANNUAL`.)

- [ ] **Step 4: Type-check sst.config.ts**

```
npx tsc --noEmit -p .
```

Expected: no errors.

- [ ] **Step 5: Commit**

```
git add sst.config.ts
git commit -m "infra: add BillingWebhookDedup table; trim unused Stripe env vars"
```

---

## Phase F — Frontend wiring

### Task F1: Create billing API client

**Files:**
- Create: `frontend/lib/api/billing.ts`
- Modify: `frontend/lib/api/index.ts`

- [ ] **Step 1: Create `frontend/lib/api/billing.ts`**

```typescript
/**
 * Billing API
 * Endpoints for Stripe checkout, customer portal, subscription, and usage.
 */

import { apiClient } from './client';

export interface SubscriptionDTO {
  plan: 'pro' | 'business' | 'enterprise' | 'locked';
  status: 'trialing' | 'active' | 'past_due' | 'canceled' | 'incomplete' | 'incomplete_expired' | 'unpaid' | 'no_subscription';
  current_period_end: string;
  trial_end: string;
  cancel_at_period_end: boolean;
  monthly_page_limit: number;
  monthly_pages_used: number;
  concurrent_job_limit: number;
  features: {
    js_rendering: boolean;
    proxy_rotation: boolean;
    webhooks: boolean;
    anti_bot: boolean;
  };
  has_billing_account: boolean;
}

export interface UsageDTO {
  pages_used: number;
  pages_limit: number;
  pages_percentage: number;
  concurrent_job_limit: number;
  billing_period_end: string;
  plan: string;
}

export interface CreateCheckoutRequest {
  plan?: 'pro' | 'business';
  interval?: 'month' | 'year';
  is_trial?: boolean;
}

export interface CreateCheckoutResponse {
  checkout_url: string;
}

export interface CreatePortalResponse {
  portal_url: string;
}

export const billingAPI = {
  getSubscription: (token: string) =>
    apiClient.get<SubscriptionDTO>('/billing/subscription', token),

  getUsage: (token: string) =>
    apiClient.get<UsageDTO>('/billing/usage', token),

  createCheckoutSession: (token: string, body: CreateCheckoutRequest) =>
    apiClient.post<CreateCheckoutResponse>('/billing/checkout', token, body),

  createPortalSession: (token: string) =>
    apiClient.post<CreatePortalResponse>('/billing/portal', token),
};
```

- [ ] **Step 2: Export from `frontend/lib/api/index.ts`**

Open `frontend/lib/api/index.ts`. Append:

```typescript
export { billingAPI } from './billing';
export type {
  SubscriptionDTO,
  UsageDTO,
  CreateCheckoutRequest,
  CreateCheckoutResponse,
  CreatePortalResponse,
} from './billing';
```

- [ ] **Step 3: Type-check**

```
cd frontend
pnpm tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/lib/api/billing.ts frontend/lib/api/index.ts
git commit -m "feat(billing): add billing API client"
```

---

### Task F2: Create API keys API client

**Files:**
- Create: `frontend/lib/api/api-keys.ts`
- Modify: `frontend/lib/api/index.ts`

- [ ] **Step 1: Create `frontend/lib/api/api-keys.ts`**

```typescript
/**
 * API Keys API
 * Endpoints for creating, listing, and revoking API keys.
 */

import { apiClient } from './client';

export interface ApiKeyListItem {
  api_key_id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  is_active: boolean;
}

export interface CreateApiKeyResponse {
  api_key_id: string;
  name: string;
  key: string;
  key_prefix: string;
  created_at: string;
  message: string;
}

export const apiKeysAPI = {
  list: (token: string) =>
    apiClient.get<{ keys: ApiKeyListItem[] }>('/api-keys', token),

  create: (token: string, name: string) =>
    apiClient.post<CreateApiKeyResponse>('/api-keys', token, { name }),

  delete: (token: string, apiKeyId: string) =>
    apiClient.delete<{ message: string }>(`/api-keys/${apiKeyId}`, token),
};
```

- [ ] **Step 2: Export from `frontend/lib/api/index.ts`**

Append:

```typescript
export { apiKeysAPI } from './api-keys';
export type { ApiKeyListItem, CreateApiKeyResponse } from './api-keys';
```

- [ ] **Step 3: Type-check**

```
cd frontend
pnpm tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/lib/api/api-keys.ts frontend/lib/api/index.ts
git commit -m "feat(api-keys): add API keys client"
```

---

### Task F3: Create billing hooks

**Files:**
- Create: `frontend/lib/hooks/useSubscription.ts`
- Modify: `frontend/lib/hooks/index.ts`

- [ ] **Step 1: Create `frontend/lib/hooks/useSubscription.ts`**

```typescript
/**
 * Billing query/mutation hooks.
 */

'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { useSession } from '@clerk/nextjs';
import { billingAPI, type SubscriptionDTO, type UsageDTO, type CreateCheckoutRequest } from '@/lib/api';

export function useSubscription() {
  const { session } = useSession();

  return useQuery<SubscriptionDTO>({
    queryKey: ['billing', 'subscription'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return billingAPI.getSubscription(token);
    },
    enabled: !!session,
    staleTime: 60_000,
    retry: (failureCount, error: any) => {
      if (error?.status === 401 || error?.status === 403) return false;
      return failureCount < 3;
    },
  });
}

export function useUsage() {
  const { session } = useSession();

  return useQuery<UsageDTO>({
    queryKey: ['billing', 'usage'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return billingAPI.getUsage(token);
    },
    enabled: !!session,
    staleTime: 30_000,
    retry: (failureCount, error: any) => {
      if (error?.status === 401 || error?.status === 403) return false;
      return failureCount < 3;
    },
  });
}

export function useStartCheckout() {
  const { session } = useSession();

  return useMutation({
    mutationFn: async (body: CreateCheckoutRequest) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return billingAPI.createCheckoutSession(token, body);
    },
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
  });
}

export function useOpenPortal() {
  const { session } = useSession();

  return useMutation({
    mutationFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return billingAPI.createPortalSession(token);
    },
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
  });
}
```

- [ ] **Step 2: Export from `frontend/lib/hooks/index.ts`**

Append:

```typescript
export {
  useSubscription,
  useUsage,
  useStartCheckout,
  useOpenPortal,
} from './useSubscription';
```

- [ ] **Step 3: Type-check**

```
cd frontend
pnpm tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/lib/hooks/useSubscription.ts frontend/lib/hooks/index.ts
git commit -m "feat(billing): add useSubscription/useUsage/useStartCheckout/useOpenPortal hooks"
```

---

### Task F4: Create API keys hooks

**Files:**
- Create: `frontend/lib/hooks/useApiKeys.ts`
- Modify: `frontend/lib/hooks/index.ts`

- [ ] **Step 1: Create `frontend/lib/hooks/useApiKeys.ts`**

```typescript
/**
 * API key query/mutation hooks.
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSession } from '@clerk/nextjs';
import { apiKeysAPI, type ApiKeyListItem, type CreateApiKeyResponse } from '@/lib/api';
import { toast } from '@/lib/toast';

export function useApiKeys() {
  const { session } = useSession();

  return useQuery<ApiKeyListItem[]>({
    queryKey: ['api-keys'],
    queryFn: async () => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      const data = await apiKeysAPI.list(token);
      return data.keys ?? [];
    },
    enabled: !!session,
    staleTime: 30_000,
  });
}

export function useCreateApiKey() {
  const { session } = useSession();
  const queryClient = useQueryClient();

  return useMutation<CreateApiKeyResponse, Error, string>({
    mutationFn: async (name: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return apiKeysAPI.create(token, name);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: (error: any) => {
      toast.error(error?.message ?? 'Failed to create API key');
    },
  });
}

export function useDeleteApiKey() {
  const { session } = useSession();
  const queryClient = useQueryClient();

  return useMutation<{ message: string }, Error, string>({
    mutationFn: async (apiKeyId: string) => {
      const token = await session?.getToken();
      if (!token) throw new Error('Not authenticated');
      return apiKeysAPI.delete(token, apiKeyId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      toast.success('API key revoked');
    },
    onError: (error: any) => {
      toast.error(error?.message ?? 'Failed to revoke API key');
    },
  });
}
```

- [ ] **Step 2: Export from index**

Append to `frontend/lib/hooks/index.ts`:

```typescript
export { useApiKeys, useCreateApiKey, useDeleteApiKey } from './useApiKeys';
```

- [ ] **Step 3: Type-check + commit**

```
cd frontend
pnpm tsc --noEmit
```

```
git add frontend/lib/hooks/useApiKeys.ts frontend/lib/hooks/index.ts
git commit -m "feat(api-keys): add useApiKeys/useCreateApiKey/useDeleteApiKey hooks"
```

---

### Task F5: Add subscription gate to middleware

**Files:**
- Create: `frontend/middleware.ts`

- [ ] **Step 1: Inspect existing middleware (if present)**

```
cat frontend/middleware.ts 2>/dev/null
```

If a middleware already exists with Clerk auth wiring, you'll merge the subscription gate into it instead of replacing. If not, create a new file.

- [ ] **Step 2: Create or replace `frontend/middleware.ts`**

```typescript
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

const isPublicRoute = createRouteMatcher([
  '/',
  '/pricing',
  '/about',
  '/contact',
  '/blog(.*)',
  '/docs(.*)',
  '/features',
  '/use-cases',
  '/privacy-policy',
  '/terms-conditions',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/api/health',
]);

const isBillingExempt = createRouteMatcher([
  '/onboarding/checkout',
  '/billing/locked',
]);

const SUBSCRIPTION_COOKIE = 'sf_sub_status';
const COOKIE_TTL_SECONDS = 60;

interface SubStatusCookie {
  status: string;
  fetched_at: number;
}

export default clerkMiddleware(async (auth, req) => {
  if (isPublicRoute(req)) {
    return NextResponse.next();
  }

  const { userId, getToken } = await auth();
  if (!userId) {
    return NextResponse.redirect(new URL('/sign-in', req.url));
  }

  if (isBillingExempt(req)) {
    return NextResponse.next();
  }

  // Read cached status cookie if fresh.
  const cookieValue = req.cookies.get(SUBSCRIPTION_COOKIE)?.value;
  let cached: SubStatusCookie | null = null;
  if (cookieValue) {
    try {
      cached = JSON.parse(cookieValue) as SubStatusCookie;
      const age = Math.floor(Date.now() / 1000) - cached.fetched_at;
      if (age > COOKIE_TTL_SECONDS) {
        cached = null;
      }
    } catch {
      cached = null;
    }
  }

  let status = cached?.status;

  if (!status) {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!apiBase) {
      // No API configured (e.g. local without env) — let the user through;
      // app will show error states from useSubscription instead.
      return NextResponse.next();
    }
    const token = await getToken();
    if (!token) {
      return NextResponse.redirect(new URL('/sign-in', req.url));
    }
    try {
      const resp = await fetch(`${apiBase}/billing/subscription`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      if (resp.ok) {
        const data = (await resp.json()) as { status?: string };
        status = data.status ?? 'no_subscription';
      } else {
        status = 'no_subscription';
      }
    } catch {
      // Network error — fail-open to avoid lockout from infra hiccups.
      return NextResponse.next();
    }
  }

  const res = redirectForStatus(status ?? 'no_subscription', req);
  if (!cached && res.headers.get('location') !== req.url) {
    const cookiePayload: SubStatusCookie = {
      status: status ?? 'no_subscription',
      fetched_at: Math.floor(Date.now() / 1000),
    };
    res.cookies.set(SUBSCRIPTION_COOKIE, JSON.stringify(cookiePayload), {
      httpOnly: true,
      sameSite: 'lax',
      maxAge: COOKIE_TTL_SECONDS,
      path: '/',
    });
  }
  return res;
});

function redirectForStatus(status: string, req: Request) {
  if (status === 'trialing' || status === 'active') {
    return NextResponse.next();
  }
  if (status === 'past_due' || status === 'incomplete') {
    return NextResponse.redirect(
      new URL('/billing/locked?reason=payment_failed', req.url)
    );
  }
  if (status === 'canceled') {
    return NextResponse.redirect(new URL('/billing/locked?reason=canceled', req.url));
  }
  // no_subscription, unpaid, incomplete_expired
  return NextResponse.redirect(new URL('/onboarding/checkout', req.url));
}

export const config = {
  matcher: ['/((?!_next|.*\\..*).*)'],
};
```

- [ ] **Step 3: Type-check**

```
cd frontend
pnpm tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```
git add frontend/middleware.ts
git commit -m "feat(billing): add subscription-status gate middleware"
```

---

### Task F6: Build /onboarding/checkout page

**Files:**
- Create: `frontend/app/(application)/onboarding/checkout/page.tsx`

- [ ] **Step 1: Create the page**

```tsx
/**
 * Onboarding Checkout Page
 * One CTA → POST /billing/checkout (plan=pro, is_trial=true) → Stripe.
 */

'use client';

import { useStartCheckout } from '@/lib/hooks';
import { Button } from '@snowforge/ui';
import { CheckCircle2, Loader2 } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

export default function OnboardingCheckoutPage() {
  const searchParams = useSearchParams();
  const cancelled = searchParams.get('cancelled') === '1';

  const startCheckout = useStartCheckout();

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="max-w-xl w-full bg-card border border-border rounded-lg p-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Start your 14-day Pro trial</h1>
          <p className="text-muted-foreground">
            Card required. We won&apos;t charge you until day 15. Cancel anytime.
          </p>
        </div>

        <ul className="space-y-2">
          {[
            '25,000 pages/month',
            'JS rendering + proxy rotation',
            'Webhook delivery',
            '5 concurrent jobs',
          ].map((feature) => (
            <li key={feature} className="flex items-center gap-2 text-sm">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              {feature}
            </li>
          ))}
        </ul>

        {cancelled && (
          <div className="bg-muted p-3 rounded text-sm text-muted-foreground">
            You cancelled the checkout. Try again whenever you&apos;re ready.
          </div>
        )}

        <Button
          size="lg"
          className="w-full"
          disabled={startCheckout.isPending}
          onClick={() =>
            startCheckout.mutate({ plan: 'pro', interval: 'month', is_trial: true })
          }
        >
          {startCheckout.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Redirecting to Stripe…
            </>
          ) : (
            'Start trial — continue to Stripe'
          )}
        </Button>

        {startCheckout.isError && (
          <div className="text-sm text-destructive">
            Couldn&apos;t start checkout. Please try again or contact support.
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          By continuing you agree to our{' '}
          <a href="/terms-conditions" className="underline">terms</a> and{' '}
          <a href="/privacy-policy" className="underline">privacy policy</a>.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check + commit**

```
cd frontend
pnpm tsc --noEmit
```

```
git add "frontend/app/(application)/onboarding/checkout/page.tsx"
git commit -m "feat(billing): /onboarding/checkout landing page"
```

---

### Task F7: Build /billing/locked page

**Files:**
- Create: `frontend/app/(application)/billing/locked/page.tsx`

- [ ] **Step 1: Create the page**

```tsx
/**
 * Billing Locked Page
 * Shown when subscription is past_due, canceled, incomplete, etc.
 * One CTA → POST /billing/portal → Stripe Customer Portal.
 */

'use client';

import { useOpenPortal } from '@/lib/hooks';
import { Button } from '@snowforge/ui';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

const REASON_COPY: Record<string, { title: string; body: string }> = {
  payment_failed: {
    title: 'Your payment failed',
    body: 'Update your payment method to keep using SnowScrape.',
  },
  canceled: {
    title: 'Your subscription was canceled',
    body: 'Resubscribe to keep using SnowScrape. Your existing data is safe.',
  },
  default: {
    title: 'Your account is on hold',
    body: 'Manage your subscription to continue.',
  },
};

export default function BillingLockedPage() {
  const searchParams = useSearchParams();
  const reason = searchParams.get('reason') ?? 'default';
  const copy = REASON_COPY[reason] ?? REASON_COPY.default;

  const openPortal = useOpenPortal();

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="max-w-xl w-full bg-card border border-border rounded-lg p-8 space-y-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-destructive" />
          <h1 className="text-2xl font-bold">{copy.title}</h1>
        </div>
        <p className="text-muted-foreground">{copy.body}</p>

        <Button
          size="lg"
          className="w-full"
          disabled={openPortal.isPending}
          onClick={() => openPortal.mutate()}
        >
          {openPortal.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Opening Stripe…
            </>
          ) : (
            'Manage subscription'
          )}
        </Button>

        {openPortal.isError && (
          <div className="text-sm text-destructive">
            Couldn&apos;t open the customer portal. Please try again.
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Need help? Email{' '}
          <a href="mailto:alex@snowforge.dev" className="underline">
            alex@snowforge.dev
          </a>.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check + commit**

```
cd frontend
pnpm tsc --noEmit
```

```
git add "frontend/app/(application)/billing/locked/page.tsx"
git commit -m "feat(billing): /billing/locked screen"
```

---

### Task F8: Rewire Settings → Billing tab

**Files:**
- Modify: `frontend/app/(application)/dashboard/settings/page.tsx`

- [ ] **Step 1: Replace Billing tab content**

In `frontend/app/(application)/dashboard/settings/page.tsx`, locate `<TabsContent value="billing" className="space-y-6">` (around line 353). Replace its entire content (everything between this opening tag and its matching `</TabsContent>`) with:

```tsx
          <TabsContent value="billing" className="space-y-6">
            <BillingTab />
          </TabsContent>
```

Then, near the top of the file (above `export default function SettingsPage()`), add:

```tsx
import { useSubscription, useUsage, useOpenPortal } from '@/lib/hooks';

function BillingTab() {
  const { data: sub, isLoading: subLoading } = useSubscription();
  const { data: usage } = useUsage();
  const openPortal = useOpenPortal();

  if (subLoading || !sub) {
    return (
      <Card>
        <CardContent className="p-6 text-muted-foreground">Loading…</CardContent>
      </Card>
    );
  }

  const planLabels: Record<string, string> = {
    pro: 'Pro',
    business: 'Business',
    enterprise: 'Enterprise',
    locked: 'Locked',
  };
  const planPrices: Record<string, string> = {
    pro: '$49/month',
    business: '$149/month',
    enterprise: 'Custom',
    locked: '—',
  };

  const statusBadge = () => {
    switch (sub.status) {
      case 'trialing':
        return <Badge variant="secondary">Trialing</Badge>;
      case 'active':
        return <Badge>Active</Badge>;
      case 'past_due':
        return <Badge variant="destructive">Past due</Badge>;
      case 'canceled':
        return <Badge variant="outline">Canceled</Badge>;
      default:
        return <Badge variant="outline">{sub.status}</Badge>;
    }
  };

  let trialBanner: React.ReactNode = null;
  if (sub.status === 'trialing' && sub.trial_end) {
    const ms = new Date(sub.trial_end).getTime() - Date.now();
    const days = Math.max(0, Math.ceil(ms / 86_400_000));
    trialBanner = (
      <div className="rounded bg-muted text-muted-foreground text-sm p-3">
        Trial ends in {days} {days === 1 ? 'day' : 'days'}.
      </div>
    );
  }
  if (sub.cancel_at_period_end) {
    trialBanner = (
      <div className="rounded bg-muted text-muted-foreground text-sm p-3">
        Your subscription is set to cancel at the end of the current period.
      </div>
    );
  }

  const pct = usage?.pages_percentage ?? 0;
  const usageColor =
    pct < 80 ? 'bg-primary' : pct < 95 ? 'bg-amber-500' : 'bg-destructive';

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Current plan</CardTitle>
          <CardDescription>Manage your subscription</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-2xl font-bold">
                  {planLabels[sub.plan] ?? sub.plan}
                </h3>
                <p className="text-muted-foreground">
                  {planPrices[sub.plan] ?? ''}
                </p>
              </div>
              {statusBadge()}
            </div>
            {trialBanner}
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => openPortal.mutate()}
              disabled={openPortal.isPending || !sub.has_billing_account}
            >
              Manage subscription
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Usage this period</CardTitle>
          <CardDescription>
            Resets on{' '}
            {usage?.billing_period_end
              ? new Date(usage.billing_period_end).toLocaleDateString()
              : '—'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between text-sm">
            <span>Pages used</span>
            <span>
              {usage?.pages_used.toLocaleString() ?? 0} /{' '}
              {usage?.pages_limit === -1
                ? 'unlimited'
                : usage?.pages_limit?.toLocaleString() ?? 0}
            </span>
          </div>
          <div className="h-2 bg-muted rounded overflow-hidden">
            <div
              className={`h-full ${usageColor} transition-all`}
              style={{ width: `${Math.min(100, pct)}%` }}
            />
          </div>
        </CardContent>
      </Card>
    </>
  );
}
```

- [ ] **Step 2: Remove the Payment Method Card and Billing History Card**

These were inside the Billing tab and have already been replaced by the `<BillingTab />` component above. Delete any remaining `<Card>` blocks that referenced "Payment Method" or "Billing History" — they're not used in the new tab.

- [ ] **Step 3: Run frontend dev server, manually verify the tab renders without crashing (with mock subscription)**

```
cd frontend
pnpm dev
```

Navigate to `http://localhost:3001/dashboard/settings`. Sign in. Click Billing tab. Confirm: page loads (will show "Loading…" or an error state if backend isn't running, both acceptable).

- [ ] **Step 4: Commit**

```
git add "frontend/app/(application)/dashboard/settings/page.tsx"
git commit -m "feat(billing): wire Settings → Billing tab to live data"
```

---

### Task F9: Build CreateApiKeyDialog (one-time secret modal)

**Files:**
- Create: `frontend/components/billing/CreateApiKeyDialog.tsx`

- [ ] **Step 1: Create the dialog**

```tsx
/**
 * CreateApiKeyDialog
 *
 * Two-step modal:
 * 1. Name input → submit
 * 2. Show raw key once (copyable) with required acknowledgment checkbox
 *    that gates closing.
 */

'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@snowforge/ui';
import { Input } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Label } from '@snowforge/ui';
import { Checkbox } from '@snowforge/ui';
import { Alert, AlertDescription } from '@snowforge/ui';
import { Copy, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useCreateApiKey } from '@/lib/hooks';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateApiKeyDialog({ open, onOpenChange }: Props) {
  const [name, setName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [copied, setCopied] = useState(false);

  const createKey = useCreateApiKey();

  const reset = () => {
    setName('');
    setCreatedKey(null);
    setAcknowledged(false);
    setCopied(false);
  };

  const handleClose = (next: boolean) => {
    if (!next) {
      // Block close while raw key is shown and not yet acknowledged.
      if (createdKey && !acknowledged) return;
      reset();
    }
    onOpenChange(next);
  };

  const handleSubmit = async () => {
    if (!name.trim()) return;
    try {
      const result = await createKey.mutateAsync(name.trim());
      setCreatedKey(result.key);
    } catch {
      // toast already fired by hook
    }
  };

  const handleCopy = async () => {
    if (!createdKey) return;
    await navigator.clipboard.writeText(createdKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        {!createdKey ? (
          <>
            <DialogHeader>
              <DialogTitle>Create API key</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <Label htmlFor="api-key-name">Name</Label>
              <Input
                id="api-key-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Production server"
                maxLength={100}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => handleClose(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!name.trim() || createKey.isPending}
              >
                {createKey.isPending ? 'Creating…' : 'Create key'}
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Save your API key</DialogTitle>
            </DialogHeader>
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This is the only time you&apos;ll see the full key. Save it
                somewhere safe now.
              </AlertDescription>
            </Alert>
            <div className="flex items-center gap-2">
              <Input
                value={createdKey}
                readOnly
                className="font-mono text-sm"
                onFocus={(e) => e.currentTarget.select()}
              />
              <Button variant="ghost" size="icon" onClick={handleCopy}>
                {copied ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="flex items-center gap-2 pt-2">
              <Checkbox
                id="ack"
                checked={acknowledged}
                onCheckedChange={(v) => setAcknowledged(!!v)}
              />
              <Label htmlFor="ack" className="text-sm cursor-pointer">
                I&apos;ve saved this key.
              </Label>
            </div>
            <DialogFooter>
              <Button
                onClick={() => handleClose(false)}
                disabled={!acknowledged}
              >
                Done
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Type-check + commit**

```
cd frontend
pnpm tsc --noEmit
```

```
git add frontend/components/billing/CreateApiKeyDialog.tsx
git commit -m "feat(api-keys): one-time-secret create-key dialog"
```

---

### Task F10: Rewire Settings → API Keys tab

**Files:**
- Modify: `frontend/app/(application)/dashboard/settings/page.tsx`

- [ ] **Step 1: Replace the API Keys tab content**

In `frontend/app/(application)/dashboard/settings/page.tsx`, locate `<TabsContent value="api-keys" className="space-y-6">`. Replace its entire content (between the open and matching close tag) with:

```tsx
          <TabsContent value="api-keys" className="space-y-6">
            <ApiKeysTab />
          </TabsContent>
```

Then, near the top of the file (alongside `BillingTab` from Task F8), add:

```tsx
import { useApiKeys, useDeleteApiKey } from '@/lib/hooks';
import { CreateApiKeyDialog } from '@/components/billing/CreateApiKeyDialog';

function ApiKeysTab() {
  const { data: keys, isLoading } = useApiKeys();
  const deleteKey = useDeleteApiKey();
  const [createOpen, setCreateOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6 text-muted-foreground">Loading…</CardContent>
      </Card>
    );
  }

  const activeKeys = (keys ?? []).filter((k) => k.is_active);
  const revokedKeys = (keys ?? []).filter((k) => !k.is_active);

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>API keys</CardTitle>
              <CardDescription>Programmatic access to SnowScrape</CardDescription>
            </div>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create API key
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {activeKeys.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Key className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">No API keys</p>
              <p className="text-sm">Create your first API key to get started</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeKeys.map((k) => (
                <div
                  key={k.api_key_id}
                  className="rounded-lg border border-border bg-card p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="font-medium">{k.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        Created {new Date(k.created_at).toLocaleDateString()}
                      </p>
                      {k.last_used_at && (
                        <p className="text-xs text-muted-foreground">
                          Last used {new Date(k.last_used_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <Badge>Active</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      value={`${k.key_prefix}…`}
                      readOnly
                      className="font-mono text-sm"
                    />
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => setConfirmDelete(k.api_key_id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {revokedKeys.length > 0 && (
            <details className="mt-6">
              <summary className="text-sm text-muted-foreground cursor-pointer">
                Revoked keys ({revokedKeys.length})
              </summary>
              <div className="space-y-2 mt-3 opacity-60">
                {revokedKeys.map((k) => (
                  <div
                    key={k.api_key_id}
                    className="rounded border border-border p-3 text-sm"
                  >
                    <span className="font-medium">{k.name}</span>
                    <span className="ml-2 text-muted-foreground font-mono">
                      {k.key_prefix}…
                    </span>
                    <Badge variant="outline" className="ml-2">
                      Revoked
                    </Badge>
                  </div>
                ))}
              </div>
            </details>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Authentication</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Include the key in the Authorization header:
          </p>
          <code className="block rounded bg-muted p-3 text-xs">
            Authorization: Bearer YOUR_API_KEY
          </code>
        </CardContent>
      </Card>

      <CreateApiKeyDialog open={createOpen} onOpenChange={setCreateOpen} />

      <Dialog
        open={!!confirmDelete}
        onOpenChange={(o) => !o && setConfirmDelete(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke API key?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This will immediately invalidate the key. Any service using it will
            start receiving 401 errors.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (!confirmDelete) return;
                await deleteKey.mutateAsync(confirmDelete);
                setConfirmDelete(null);
              }}
            >
              Revoke
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

- [ ] **Step 2: Remove orphaned imports + state**

In the same file, near the top of the existing default-export component, find any old API-key-related state — `apiKeys`, `showApiKey`, `copiedKey`, `keyToDelete`, `deleteDialogOpen` — and any helper functions like `handleCreateApiKey`, `toggleShowKey`, `copyApiKey`, `maskApiKey`. Delete them. The new `ApiKeysTab` and `CreateApiKeyDialog` own this state internally.

Also remove unused imports left over from the deleted code (run `pnpm tsc --noEmit` and follow the errors).

- [ ] **Step 3: Type-check + commit**

```
cd frontend
pnpm tsc --noEmit
```

```
git add "frontend/app/(application)/dashboard/settings/page.tsx"
git commit -m "feat(api-keys): wire Settings → API Keys tab to live data"
```

---

### Task F11: Update pricing page

**Files:**
- Modify: `frontend/app/(marketing)/pricing/page.tsx`
- Create: `frontend/components/marketing/PricingCTA.tsx`

- [ ] **Step 1: Create the PricingCTA component**

```tsx
/**
 * PricingCTA
 * Routes signed-out users to Clerk sign-up, signed-in users to portal/onboarding.
 */

'use client';

import { useUser } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { Button } from '@snowforge/ui';
import { useSubscription, useOpenPortal } from '@/lib/hooks';

interface Props {
  plan: 'pro' | 'business' | 'enterprise';
  variant?: 'default' | 'outline';
}

export function PricingCTA({ plan, variant = 'default' }: Props) {
  const { isSignedIn, isLoaded } = useUser();
  const router = useRouter();
  const { data: sub } = useSubscription();
  const openPortal = useOpenPortal();

  if (plan === 'enterprise') {
    return (
      <Button
        variant={variant}
        className="w-full"
        onClick={() => {
          window.location.href = 'mailto:alex@snowforge.dev?subject=SnowScrape Enterprise';
        }}
      >
        Contact us
      </Button>
    );
  }

  const label = plan === 'pro' ? 'Start 14-day trial' : 'Choose Business';

  if (!isLoaded) {
    return <Button variant={variant} className="w-full" disabled>Loading…</Button>;
  }

  if (!isSignedIn) {
    return (
      <Button
        variant={variant}
        className="w-full"
        onClick={() => router.push('/sign-up')}
      >
        {label}
      </Button>
    );
  }

  const status = sub?.status;
  const hasActiveSub = status === 'trialing' || status === 'active';

  if (hasActiveSub) {
    return (
      <Button
        variant={variant}
        className="w-full"
        disabled={openPortal.isPending}
        onClick={() => openPortal.mutate()}
      >
        Manage subscription
      </Button>
    );
  }

  return (
    <Button
      variant={variant}
      className="w-full"
      onClick={() => router.push('/onboarding/checkout')}
    >
      {label}
    </Button>
  );
}
```

- [ ] **Step 2: Edit pricing page**

In `frontend/app/(marketing)/pricing/page.tsx`:

1. Delete the entire Starter plan card block (line 34-51 area in the current source — confirm by reading it first; it's the `{/* Starter Plan */}` section).
2. Above the remaining plan grid, add a hero section:

```tsx
<div className="text-center mb-10">
  <h2 className="text-2xl font-semibold mb-2">
    Start with a 14-day free trial of Pro
  </h2>
  <p className="text-muted-foreground">
    No charge until day 15. Cancel anytime. Card required.
  </p>
</div>
```

3. Update the grid container's column class from 4 columns to 3 columns:
   - Find: `grid gap-8 lg:grid-cols-4` (or similar) and change to `grid gap-8 lg:grid-cols-3`.
4. Replace each plan card's CTA button with `<PricingCTA plan="pro" />`, `<PricingCTA plan="business" />`, `<PricingCTA plan="enterprise" variant="outline" />` respectively.
5. If a feature comparison table exists below the cards, delete its Starter column.

Add `import { PricingCTA } from '@/components/marketing/PricingCTA';` at the top of the file.

- [ ] **Step 3: Type-check, dev-run smoke**

```
cd frontend
pnpm tsc --noEmit
pnpm dev
```

Navigate to `http://localhost:3001/pricing`. Confirm: 3 cards, no Starter card, hero copy renders, signed-out CTA opens sign-up.

- [ ] **Step 4: Commit**

```
git add "frontend/app/(marketing)/pricing/page.tsx" frontend/components/marketing/PricingCTA.tsx
git commit -m "feat(pricing): drop Starter, add 14-day-trial hero, route CTAs"
```

---

### Task F12: Frontend tests

**Files:**
- Create: `frontend/lib/__tests__/api/billing.test.ts`
- Create: `frontend/lib/__tests__/hooks/useSubscription.test.ts`

- [ ] **Step 1: Write billing API client tests**

Create `frontend/lib/__tests__/api/billing.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { billingAPI } from '@/lib/api/billing';

beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
  vi.restoreAllMocks();
});

describe('billingAPI.getSubscription', () => {
  it('returns parsed subscription dto', async () => {
    const mockJson = {
      plan: 'pro',
      status: 'trialing',
      current_period_end: '2026-06-01',
      trial_end: '2026-05-20',
      cancel_at_period_end: false,
      monthly_page_limit: 25000,
      monthly_pages_used: 100,
      concurrent_job_limit: 5,
      features: {
        js_rendering: true,
        proxy_rotation: true,
        webhooks: true,
        anti_bot: false,
      },
      has_billing_account: true,
    };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => mockJson,
    } as any);

    const result = await billingAPI.getSubscription('test-token');
    expect(result).toEqual(mockJson);
    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.test/billing/subscription',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
        }),
      })
    );
  });
});

describe('billingAPI.createCheckoutSession', () => {
  it('posts is_trial flag and returns checkout_url', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ checkout_url: 'https://stripe.test/cs' }),
    } as any);

    const result = await billingAPI.createCheckoutSession('t', {
      plan: 'pro',
      is_trial: true,
    });
    expect(result.checkout_url).toBe('https://stripe.test/cs');
    const call = (global.fetch as any).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body).toEqual({ plan: 'pro', is_trial: true });
  });
});
```

- [ ] **Step 2: Run tests**

```
cd frontend
pnpm test lib/__tests__/api/billing.test.ts
```

Expected: PASS.

- [ ] **Step 3: Write useSubscription hook test**

Create `frontend/lib/__tests__/hooks/useSubscription.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useSubscription } from '@/lib/hooks/useSubscription';

vi.mock('@clerk/nextjs', () => ({
  useSession: () => ({
    session: { getToken: async () => 'test-token' },
  }),
}));

vi.mock('@/lib/api', () => ({
  billingAPI: {
    getSubscription: vi.fn(),
  },
}));

import { billingAPI } from '@/lib/api';

beforeEach(() => {
  vi.clearAllMocks();
  process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.test';
});

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useSubscription', () => {
  it('returns subscription data on success', async () => {
    (billingAPI.getSubscription as any).mockResolvedValue({
      plan: 'pro',
      status: 'trialing',
      monthly_page_limit: 25000,
      monthly_pages_used: 0,
    });
    const { result } = renderHook(() => useSubscription(), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.plan).toBe('pro');
    expect(result.current.data?.status).toBe('trialing');
  });
});
```

- [ ] **Step 4: Run hook test**

```
cd frontend
pnpm test lib/__tests__/hooks/useSubscription.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```
git add frontend/lib/__tests__
git commit -m "test(billing): unit tests for billingAPI and useSubscription"
```

---

### Task F13: Playwright E2E for redirect flows + create-key modal

**Files:**
- Create: `frontend/e2e/billing-flow.spec.ts`

- [ ] **Step 1: Create the spec**

```typescript
import { test, expect } from '@playwright/test';

/**
 * NOTE: Requires a Clerk test user pre-seeded for the test environment.
 * Set CLERK_TEST_EMAIL and CLERK_TEST_PASSWORD in .env.test, and ensure
 * the Clerk dashboard has the test user without a SnowScrape subscription.
 */

test.describe('Billing flow E2E', () => {
  test('signed-in user with no subscription is redirected to /onboarding/checkout', async ({
    page,
  }) => {
    await page.goto('/sign-in');
    await page.fill('input[name="identifier"]', process.env.CLERK_TEST_EMAIL!);
    await page.click('button[type="submit"]');
    await page.fill('input[name="password"]', process.env.CLERK_TEST_PASSWORD!);
    await page.click('button[type="submit"]');

    // Land somewhere; middleware should redirect to /onboarding/checkout.
    await page.waitForURL(/\/onboarding\/checkout/, { timeout: 15_000 });
    await expect(page.getByRole('heading', { name: /14-day Pro trial/i })).toBeVisible();
  });

  test('create-API-key modal shows raw key once and gates close', async ({ page }) => {
    test.fixme(true, 'Requires authenticated session with active subscription — set up in CI before enabling');
  });
});
```

- [ ] **Step 2: Add Playwright config (if not already pointing at e2e/)**

Verify `frontend/playwright.config.ts` includes `e2e/` in its `testDir`. If not, update accordingly.

- [ ] **Step 3: Run smoke**

```
cd frontend
pnpm test:e2e --grep "no subscription is redirected"
```

Expected: this test will be skipped or fail without a configured test user. Document the requirement in the test's NOTE block (already done above) and leave it as a CI prerequisite.

- [ ] **Step 4: Commit**

```
git add frontend/e2e/billing-flow.spec.ts
git commit -m "test(billing): playwright spec for onboarding redirect + key modal"
```

---

## Phase O — Operations (Stripe + Doppler + deploy)

### Task O1: Provision Stripe products and prices in TEST mode

**Files:** none (Stripe dashboard work)

- [ ] **Step 1: Switch the SnowForge LLC Stripe dashboard to test mode** (toggle in upper right)

- [ ] **Step 2: Create the SnowScrape Pro product**

In Products → Add product:
- Name: `SnowScrape Pro`
- Description: `25,000 pages/month + JS rendering + proxy rotation + webhooks`
- Pricing model: Standard pricing
- Price: `$49.00 USD`, monthly recurring
- **Add metadata to the PRODUCT:** `tier=pro`

Save. Capture the resulting `price_test_...` ID into a scratch note (will need for Doppler in O3).

- [ ] **Step 3: Create the SnowScrape Business product**

Same flow:
- Name: `SnowScrape Business`
- Description: `100,000 pages/month + everything in Pro + anti-bot`
- Price: `$149.00 USD`, monthly recurring
- **Metadata on PRODUCT:** `tier=business`

Save. Capture `price_test_...` ID.

- [ ] **Step 4: Configure the Customer Portal (test mode)**

Settings → Billing → Customer portal:
- ✓ Enable "Customers can cancel subscriptions" → at end of billing period
- ✓ Enable "Customers can switch plans" → both Pro and Business prices selected
- ✓ Enable "Customers can update payment methods"
- ✓ Enable "Show invoice history" + "Allow invoice download"
- ✗ Disable promotion codes
- Set default return URL: `http://localhost:3001/dashboard/settings`

Save.

- [ ] **Step 5: Document the price IDs**

In a temporary scratch file (NOT committed; e.g. `~/.snowscrape-stripe-ids-dev.txt`), record:

```
STRIPE_PRICE_PRO_MONTHLY (test) = price_test_xxxxx
STRIPE_PRICE_BUSINESS_MONTHLY (test) = price_test_yyyyy
```

These go into Doppler in Task O3.

---

### Task O2: Deploy backend to dev (initial — gets the webhook URL)

**Files:** none (deploy operation)

- [ ] **Step 1: Verify Doppler dev project has at least empty placeholders for new vars**

```
doppler secrets --project sf-snowscrape --config dev get STRIPE_PRICE_PRO_MONTHLY STRIPE_PRICE_BUSINESS_MONTHLY STRIPE_WEBHOOK_SECRET STRIPE_SECRET_KEY
```

If any are missing, add empty values so the SST deploy doesn't fail on missing env. We'll fill them in O3.

```
doppler secrets set --project sf-snowscrape --config dev STRIPE_SECRET_KEY="" STRIPE_WEBHOOK_SECRET="" STRIPE_PRICE_PRO_MONTHLY="" STRIPE_PRICE_BUSINESS_MONTHLY=""
```

- [ ] **Step 2: Deploy SST to dev**

```
doppler run --project sf-snowscrape --config dev -- npx sst deploy --stage dev
```

Expected: SST output shows `Subscriptions`, `ApiKeys`, `BillingWebhookDedup` as new resources. Capture the API Gateway URL from the output (looks like `https://<id>.execute-api.us-east-2.amazonaws.com`).

- [ ] **Step 3: Note the webhook URL**

Append the webhook URL to your scratch file:

```
SNOWSCRAPE_DEV_WEBHOOK_URL = https://<api-id>.execute-api.us-east-2.amazonaws.com/billing/webhook
```

---

### Task O3: Wire Stripe webhook + populate Doppler dev

**Files:** none (Stripe + Doppler)

- [ ] **Step 1: Register the webhook in Stripe (test mode)**

Stripe dashboard → Developers → Webhooks → Add endpoint:
- Endpoint URL: the dev webhook URL from O2
- Events to send (5 total):
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`

Save. Click "Reveal signing secret" → capture `whsec_test_...`.

- [ ] **Step 2: Populate Doppler dev**

```
doppler secrets set --project sf-snowscrape --config dev \
  STRIPE_SECRET_KEY="sk_test_xxxxx" \
  STRIPE_WEBHOOK_SECRET="whsec_test_xxxxx" \
  STRIPE_PRICE_PRO_MONTHLY="price_test_xxxxx" \
  STRIPE_PRICE_BUSINESS_MONTHLY="price_test_yyyyy"
```

(Replace placeholder values with the real ones from O1 and O3.)

- [ ] **Step 3: Re-deploy so the Lambda picks up the new env**

```
doppler run --project sf-snowscrape --config dev -- npx sst deploy --stage dev
```

Expected: same output, only Lambda env updates.

---

### Task O4: Smoke test dev end-to-end

**Files:** none

- [ ] **Step 1: Set frontend env to point at dev API**

In `frontend/.env.local` (gitignored):

```
NEXT_PUBLIC_API_BASE_URL=https://<api-id>.execute-api.us-east-2.amazonaws.com
```

- [ ] **Step 2: Run dev frontend**

```
cd frontend
pnpm dev
```

- [ ] **Step 3: Click through the smoke checklist**

Run each item and check off as it passes:

- [ ] New user signup via Clerk → middleware redirects to `/onboarding/checkout`
- [ ] Click "Start trial — continue to Stripe" → redirected to Stripe Checkout
- [ ] Pay with test card `4242 4242 4242 4242`, any future date, any CVC → returns to `/dashboard?checkout=success`
- [ ] Verify Subscriptions row exists in DynamoDB:
  ```
  aws dynamodb get-item --table-name snowscrape-dev-Subscriptions --key '{"user_id":{"S":"<user-id>"}}' --region us-east-2
  ```
  Confirm `status=trialing`, `trial_end` populated.
- [ ] Create a job from the dashboard → succeeds
- [ ] Settings → Billing → confirm real plan name, real usage progress bar, "Trial ends in N days" banner
- [ ] In Stripe dashboard → Customers → click the test customer → "Advance test clock" by 15 days → wait ~30 seconds → check Subscriptions row again, confirm `status=active`, `monthly_pages_used=0`
- [ ] Settings → API Keys → "Create API key" → modal shows raw `sk_live_...` key with copy + "I've saved" checkbox → close → list shows masked prefix only
- [ ] Settings → Billing → "Manage subscription" → opens Stripe Customer Portal → cancel → returns → app still usable, banner shows "Your subscription is set to cancel..."
- [ ] In Stripe dashboard → simulate failed payment (decline test card `4000 0000 0000 0341`) on a different test user → `past_due` status → next request → redirect to `/billing/locked?reason=payment_failed`
- [ ] In Stripe dashboard → Webhooks → pick a recent successful delivery → click "Resend" → verify CloudWatch logs for the dispatch Lambda show `Duplicate webhook ignored`

If any item fails, debug and re-run before proceeding.

---

### Task O5: Provision LIVE Stripe + Doppler prd + deploy prd

**Files:** none

- [ ] **Step 1: In Stripe dashboard, switch to LIVE mode** (toggle in upper right)

- [ ] **Step 2: Repeat O1's steps 2-5 in live mode**

Same steps; new `price_...` IDs (live mode).

- [ ] **Step 3: Deploy SST to prd**

```
doppler run --project sf-snowscrape --config prd -- npx sst deploy --stage prod
```

Capture the prd API Gateway URL.

- [ ] **Step 4: Repeat O3 in live mode**

Register the prd webhook URL with the 5 events. Capture the live `whsec_live_...` and `sk_live_...`. Populate Doppler prd:

```
doppler secrets set --project sf-snowscrape --config prd \
  STRIPE_SECRET_KEY="sk_live_xxxxx" \
  STRIPE_WEBHOOK_SECRET="whsec_live_xxxxx" \
  STRIPE_PRICE_PRO_MONTHLY="price_live_xxxxx" \
  STRIPE_PRICE_BUSINESS_MONTHLY="price_live_yyyyy"
```

Re-deploy so the env propagates:

```
doppler run --project sf-snowscrape --config prd -- npx sst deploy --stage prod
```

- [ ] **Step 5: Verify CORS origins for prd**

In `sst.config.ts`, confirm the `corsOrigins.prod` (or equivalent) array includes the prd frontend domain. If missing, add it, re-deploy.

- [ ] **Step 6: Deploy frontend to Vercel prod**

```
cd frontend
vercel --prod
```

(Or use the project's normal Vercel pipeline.)

- [ ] **Step 7: Live smoke test**

Run a single live transaction:
- Sign up a brand-new account on prd with your own email.
- Complete checkout with your real card.
- Verify Subscriptions row, `status=trialing`.
- In Stripe → cancel the subscription.
- In Stripe → refund the (zero-amount) trial invoice if any was issued, then issue a manual refund or void if you accidentally got charged. **It is intentional that the trial means no immediate charge** — you should NOT see a $49 charge during trial. If you do, something is wrong with the trial config; investigate before declaring done.

If everything looks clean, mark prd shipped.

---

## Phase D — Documentation

### Task D1: Update INFRASTRUCTURE.md

**Files:**
- Modify: `docs/INFRASTRUCTURE.md`

- [ ] **Step 1: Add Subscriptions, ApiKeys, BillingWebhookDedup to the DynamoDB tables section**

In `docs/INFRASTRUCTURE.md`, locate the DynamoDB tables section. Add three table entries with the same format as existing ones, recording: name, partition key, GSIs, encryption, PITR, TTL, purpose. Include the SnowScrape billing flow diagram (signup → middleware → checkout → webhook → Subscriptions row).

- [ ] **Step 2: Add Stripe env vars to the env vars section**

Add a "Stripe (from Doppler `sf-snowscrape`)" subsection listing: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_BUSINESS_MONTHLY`.

- [ ] **Step 3: Add Customer Portal config screenshot/notes**

Add a Customer Portal subsection with the exact toggle settings used (cancellation enabled, plan switching enabled, etc.) so anyone re-creating the env can match it.

- [ ] **Step 4: Add Change Log entry + update Last Updated date**

Per `.claude/CLAUDE.md` rules, append a Change Log entry like:

```
| 2026-05-06 | Billing MVP shipped | Added Subscriptions, ApiKeys, BillingWebhookDedup tables; provisioned Stripe products + webhooks in test and live modes; trial-only entry flow | Alex Diaz |
```

Update the "Last Updated" header date.

- [ ] **Step 5: Commit**

```
git add docs/INFRASTRUCTURE.md
git commit -m "docs: document Billing MVP infra (tables, Stripe, portal config)"
```

---

### Task D2: Update PROGRESS.md and openapi.yml

**Files:**
- Modify: `PROGRESS.md`
- Modify: `backend/openapi.yml`

- [ ] **Step 1: Update PROGRESS.md**

Move "Billing / Stripe Integration" from "What's NOT DONE" to "What's DONE", with a one-line summary. Update the launch readiness percentage from ~70-75% to ~85%. Update the Estimates table to remove the billing line.

- [ ] **Step 2: Update openapi.yml**

In `backend/openapi.yml`, add path entries for:
- `POST /billing/checkout`
- `POST /billing/portal`
- `POST /billing/webhook` (note: not user-facing; mark as internal)
- `GET /billing/subscription`
- `GET /billing/usage`
- `POST /api-keys`
- `GET /api-keys`
- `DELETE /api-keys/{api_key_id}`

Use the same response schema style as existing routes. Reference SubscriptionDTO, UsageDTO from frontend types as inspiration for response bodies.

- [ ] **Step 3: Commit**

```
git add PROGRESS.md backend/openapi.yml
git commit -m "docs: update PROGRESS + openapi for Billing MVP"
```

---

### Task D3: Final verification

**Files:** none

- [ ] **Step 1: Run all backend tests**

```
cd backend
uv run pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 2: Run all frontend tests**

```
cd frontend
pnpm test
pnpm lint
```

Expected: all PASS, no lint errors.

- [ ] **Step 3: Type-check both ends**

```
cd frontend
pnpm tsc --noEmit
```

```
npx tsc --noEmit -p .
```

Expected: no errors.

- [ ] **Step 4: Confirm dev + prd deploys are healthy**

Spot-check:
- Visit dev frontend → click through onboarding → verify checkout completes
- Visit prd frontend → confirm `/pricing` renders correctly, signed-out flow works
- Stripe → Webhooks → confirm both endpoints (dev + prd) show recent successful deliveries

- [ ] **Step 5: Final commit (if anything moved)**

```
git status
# If clean, no commit needed.
```

---

## Self-Review Checklist (run before declaring plan complete)

- **Spec coverage**
  - § Subscription state machine → Task B2 ✓
  - § Signup → checkout flow → Tasks F5, F6, B4 ✓
  - § Settings page wiring → Tasks F8, F9, F10 ✓
  - § Pricing page revisions → Task F11 ✓
  - § Webhook hardening → Tasks B3, B4 ✓
  - § Operations → Phase O ✓
  - § Read-only carve-out → Task B5 ✓
  - § Prerequisites → noted in plan header ✓
- **Placeholders:** Every "Step" contains code or commands; no TBDs.
- **Type consistency:** `is_subscription_active`, `_default_subscription`, `PLAN_LIMITS["locked"]`, `BillingWebhookDedup` are spelled identically across all task references.

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-06-snowscrape-billing-mvp-plan.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Best for parallel-to-SnowPipe work since each task is small and reviewable.

2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

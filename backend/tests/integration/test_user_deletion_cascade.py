"""
Integration tests for _handle_user_deleted cascade.
Uses moto-mocked DynamoDB (via the shared dynamodb_client fixture) and
mocks stripe.Subscription.cancel.

Seed layout for user-x:
  - 1 Subscriptions row (with stripe_subscription_id)
  - 2 ApiKeys
  - 3 Jobs (each with 2 Urls → 6 Urls total)
  - 1 Template
  - 1 Webhook (with 2 WebhookDeliveries)
"""
import pytest
from unittest.mock import patch, MagicMock
import stripe as stripe_lib


# ─── Fixtures ─────────────────────────────────────────────────────────────────

USER_ID = "user-x"
STRIPE_SUB_ID = "sub_cascade_test"

@pytest.fixture
def seeded_user(dynamodb_client):
	"""Seed all tables with data for USER_ID and return table references."""
	tables = {
		"subscriptions": dynamodb_client.Table("SnowscrapeSubscriptions-test"),
		"api_keys": dynamodb_client.Table("SnowscrapeApiKeys-test"),
		"jobs": dynamodb_client.Table("SnowscrapeJobs-test"),
		"urls": dynamodb_client.Table("SnowscrapeUrls-test"),
		"templates": dynamodb_client.Table("SnowscrapeTemplates-test"),
		"webhooks": dynamodb_client.Table("SnowscrapeWebhooks-test"),
		"webhook_deliveries": dynamodb_client.Table("SnowscrapeWebhookDeliveries-test"),
	}

	# Subscriptions
	tables["subscriptions"].put_item(Item={
		"user_id": USER_ID,
		"plan": "pro",
		"status": "trialing",
		"stripe_customer_id": "cus_cascade_test",
		"stripe_subscription_id": STRIPE_SUB_ID,
	})

	# API Keys
	for i in range(1, 3):
		tables["api_keys"].put_item(Item={
			"api_key_id": f"key-x-{i}",
			"user_id": USER_ID,
			"key_hash": f"hash-x-{i}",
			"name": f"Key {i}",
		})

	# Jobs + URLs
	for j in range(1, 4):
		job_id = f"job-x-{j}"
		tables["jobs"].put_item(Item={
			"job_id": job_id,
			"user_id": USER_ID,
			"name": f"Job {j}",
			"status": "ready",
		})
		for u in range(1, 3):
			tables["urls"].put_item(Item={
				"job_id": job_id,
				"url": f"https://example.com/job{j}/page{u}",
				"status": "ready",
			})

	# Template
	tables["templates"].put_item(Item={
		"template_id": "tmpl-x-1",
		"user_id": USER_ID,
		"name": "My Template",
	})

	# Webhook
	tables["webhooks"].put_item(Item={
		"webhook_id": "wh-x-1",
		"user_id": USER_ID,
		"url": "https://hooks.example.com/wh1",
	})

	# Webhook Deliveries (keyed by webhook_id)
	for d in range(1, 3):
		tables["webhook_deliveries"].put_item(Item={
			"delivery_id": f"del-x-{d}",
			"webhook_id": "wh-x-1",
			"timestamp": 1700000000 + d,
			"status": "delivered",
		})

	return tables


# ─── Happy Path: Full Cascade ──────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.aws
class TestFullCascade:
	def test_all_rows_deleted_after_cascade(
		self, dynamodb_client, mock_env_vars, seeded_user
	):
		from clerk_webhook_handler import _handle_user_deleted

		with patch("clerk_webhook_handler.stripe") as mock_stripe:
			mock_stripe.Subscription.cancel = MagicMock()
			mock_stripe.InvalidRequestError = stripe_lib.InvalidRequestError
			_handle_user_deleted({"id": USER_ID})

		# Stripe cancel called with correct sub_id
		mock_stripe.Subscription.cancel.assert_called_once_with(STRIPE_SUB_ID)

		tables = seeded_user

		# Subscriptions row gone
		assert tables["subscriptions"].get_item(
			Key={"user_id": USER_ID}
		).get("Item") is None

		# API keys gone (both)
		for i in range(1, 3):
			assert tables["api_keys"].get_item(
				Key={"api_key_id": f"key-x-{i}"}
			).get("Item") is None

		# Jobs gone (all 3)
		for j in range(1, 4):
			assert tables["jobs"].get_item(
				Key={"job_id": f"job-x-{j}"}
			).get("Item") is None

		# URLs gone (all 6)
		for j in range(1, 4):
			for u in range(1, 3):
				result = tables["urls"].get_item(Key={
					"job_id": f"job-x-{j}",
					"url": f"https://example.com/job{j}/page{u}",
				}).get("Item")
				assert result is None, f"URL still present: job-x-{j}/page{u}"

		# Template gone
		assert tables["templates"].get_item(
			Key={"template_id": "tmpl-x-1"}
		).get("Item") is None

		# Webhook gone
		assert tables["webhooks"].get_item(
			Key={"webhook_id": "wh-x-1"}
		).get("Item") is None

		# Webhook deliveries gone
		for d in range(1, 3):
			assert tables["webhook_deliveries"].get_item(
				Key={"delivery_id": f"del-x-{d}"}
			).get("Item") is None

	def test_unrelated_user_data_untouched(
		self, dynamodb_client, mock_env_vars, seeded_user
	):
		"""Rows belonging to a different user must not be deleted."""
		# Seed a second user
		tables = seeded_user
		other_user = "user-other"
		tables["subscriptions"].put_item(Item={
			"user_id": other_user,
			"plan": "pro",
			"status": "active",
			"stripe_customer_id": "cus_other",
			"stripe_subscription_id": "",
		})
		tables["jobs"].put_item(Item={
			"job_id": "job-other-1",
			"user_id": other_user,
			"name": "Other Job",
			"status": "ready",
		})

		from clerk_webhook_handler import _handle_user_deleted
		with patch("clerk_webhook_handler.stripe") as mock_stripe:
			mock_stripe.Subscription.cancel = MagicMock()
			mock_stripe.InvalidRequestError = stripe_lib.InvalidRequestError
			_handle_user_deleted({"id": USER_ID})

		# Other user's rows still present
		assert tables["subscriptions"].get_item(
			Key={"user_id": other_user}
		).get("Item") is not None
		assert tables["jobs"].get_item(
			Key={"job_id": "job-other-1"}
		).get("Item") is not None


# ─── Stripe Already-Canceled Path ─────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.aws
class TestStripeAlreadyCanceled:
	def test_no_such_subscription_error_is_swallowed(
		self, dynamodb_client, mock_env_vars, seeded_user
	):
		"""
		If Stripe raises InvalidRequestError("No such subscription: ..."),
		the cascade should continue without re-raising.
		"""
		from clerk_webhook_handler import _handle_user_deleted

		def fake_cancel(sub_id):
			raise stripe_lib.InvalidRequestError(
				f"No such subscription: {sub_id}", param="id"
			)

		with patch("clerk_webhook_handler.stripe") as mock_stripe:
			mock_stripe.Subscription.cancel = fake_cancel
			mock_stripe.InvalidRequestError = stripe_lib.InvalidRequestError
			# Should not raise
			_handle_user_deleted({"id": USER_ID})

		# DB rows should still be deleted
		tables = seeded_user
		assert tables["subscriptions"].get_item(
			Key={"user_id": USER_ID}
		).get("Item") is None
		assert tables["jobs"].get_item(
			Key={"job_id": "job-x-1"}
		).get("Item") is None

	def test_other_stripe_error_propagates(
		self, dynamodb_client, mock_env_vars, seeded_user
	):
		"""
		A non-"No such subscription" InvalidRequestError should re-raise
		so the webhook retries.
		"""
		from clerk_webhook_handler import _handle_user_deleted

		def fake_cancel(sub_id):
			raise stripe_lib.InvalidRequestError(
				"Subscription is incomplete and cannot be canceled", param="status"
			)

		with patch("clerk_webhook_handler.stripe") as mock_stripe:
			mock_stripe.Subscription.cancel = fake_cancel
			mock_stripe.InvalidRequestError = stripe_lib.InvalidRequestError
			with pytest.raises(stripe_lib.InvalidRequestError):
				_handle_user_deleted({"id": USER_ID})


# ─── No-op When User Has No Subscription ──────────────────────────────────────

@pytest.mark.integration
@pytest.mark.aws
class TestUserWithoutSubscription:
	def test_cascade_runs_without_stripe_cancel_when_no_sub(
		self, dynamodb_client, mock_env_vars
	):
		"""
		If the user has no stripe_subscription_id, stripe.Subscription.cancel
		must NOT be called, and cascade still completes cleanly.
		"""
		tables = {
			"subscriptions": dynamodb_client.Table("SnowscrapeSubscriptions-test"),
			"jobs": dynamodb_client.Table("SnowscrapeJobs-test"),
		}
		user_no_sub = "user-nosub"
		tables["subscriptions"].put_item(Item={
			"user_id": user_no_sub,
			"plan": "locked",
			"status": "no_subscription",
			# Omit stripe_customer_id / stripe_subscription_id to avoid GSI empty-string rejection
		})
		tables["jobs"].put_item(Item={
			"job_id": "job-nosub-1",
			"user_id": user_no_sub,
			"name": "Orphan Job",
			"status": "ready",
		})

		from clerk_webhook_handler import _handle_user_deleted
		with patch("clerk_webhook_handler.stripe") as mock_stripe:
			mock_stripe.Subscription.cancel = MagicMock()
			mock_stripe.InvalidRequestError = stripe_lib.InvalidRequestError
			_handle_user_deleted({"id": user_no_sub})

		mock_stripe.Subscription.cancel.assert_not_called()
		assert tables["subscriptions"].get_item(
			Key={"user_id": user_no_sub}
		).get("Item") is None
		assert tables["jobs"].get_item(
			Key={"job_id": "job-nosub-1"}
		).get("Item") is None

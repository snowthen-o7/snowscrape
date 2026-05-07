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
		"trial_end": 1701209600,
		"cancel_at_period_end": False,
		"status": "trialing",
		"id": "sub_test_cko1",
		"customer": "cus_test_cko1",
	}[k]
	sub.get.side_effect = lambda k, default=None: {
		"trial_end": 1701209600,
		"cancel_at_period_end": False,
	}.get(k, default)
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
		end_epoch = int(dt.datetime.fromisoformat(original_period_end.replace("Z", "+00:00")).timestamp())
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

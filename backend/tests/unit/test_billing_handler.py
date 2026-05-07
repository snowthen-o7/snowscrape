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

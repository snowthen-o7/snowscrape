"""Unit tests for the clerk_webhook_handler.py user.deleted cascade.

The existing test_clerk_webhook.py covers the entry point (`handle_clerk_webhook`)
but mocks `_handle_user_deleted` out entirely, so the GDPR-grade account-deletion
cascade was untested. This file characterizes that cascade and its helpers:

- `_handle_user_deleted`: Stripe-cancel-before-DB ordering, the empty-sub skip,
  the "No such subscription" tolerance vs. re-raise on other Stripe errors, the
  early-return on a missing user id, and the job_ids/webhook_ids threading between
  the per-table deletion helpers.
- Per-table deletion helpers: item->key mapping, the empty-input short circuits,
  and the fail-closed re-raise (which is what lets the entry point roll back the
  dedup row so Clerk retries).
- Low-level helpers: `_batch_delete` 25-item chunking, and `_scan_gsi` /
  `_scan_filter_user` LastEvaluatedKey pagination.

All tests are mock-based (no moto) so they assert behavioral contracts directly
rather than round-tripping real tables.
"""
import os
from unittest.mock import patch, MagicMock, call

import pytest
import stripe

import clerk_webhook_handler as cwh


# ─── _handle_user_deleted ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestHandleUserDeleted:
	def test_missing_user_id_returns_early_with_no_side_effects(self):
		"""A user.deleted with no id must not touch Stripe or any table."""
		with patch.object(cwh, "get_subscription") as mock_get_sub, \
			patch.object(cwh.stripe, "Subscription") as mock_stripe_sub, \
			patch.object(cwh, "_delete_subscriptions_row") as mock_del_subs:
			cwh._handle_user_deleted({})
			cwh._handle_user_deleted({"id": ""})
		mock_get_sub.assert_not_called()
		mock_stripe_sub.cancel.assert_not_called()
		mock_del_subs.assert_not_called()

	def test_cancels_stripe_before_touching_the_database(self):
		"""Billing must stop before any DB row is deleted (comment-documented order)."""
		order = []
		with patch.object(cwh, "get_subscription",
						   return_value={"stripe_subscription_id": "sub_123"}), \
			patch.object(cwh.stripe, "Subscription") as mock_stripe_sub, \
			patch.object(cwh, "_delete_subscriptions_row",
						 side_effect=lambda *a, **k: order.append("db") or 1), \
			patch.object(cwh, "_delete_api_keys_for_user", return_value=0), \
			patch.object(cwh, "_delete_jobs_for_user", return_value=([], 0)), \
			patch.object(cwh, "_delete_urls_for_jobs", return_value=0), \
			patch.object(cwh, "_delete_templates_for_user", return_value=0), \
			patch.object(cwh, "_delete_webhooks_for_user", return_value=(0, [])), \
			patch.object(cwh, "_delete_webhook_deliveries_for_user", return_value=0):
			mock_stripe_sub.cancel.side_effect = lambda *a, **k: order.append("stripe")
			cwh._handle_user_deleted({"id": "user-1"})

		mock_stripe_sub.cancel.assert_called_once_with("sub_123")
		# Cancel must come first, then the (first) DB delete. _delete_subscriptions_row
		# is the first helper called, so a "db" before "stripe" means a reorder bug.
		assert order == ["stripe", "db"], "Stripe cancel must precede DB deletes"

	def test_empty_stripe_subscription_id_skips_cancel_but_still_deletes(self):
		"""A user with no Stripe sub (locked sentinel) still cascade-deletes rows."""
		with patch.object(cwh, "get_subscription",
						   return_value={"stripe_subscription_id": ""}), \
			patch.object(cwh.stripe, "Subscription") as mock_stripe_sub, \
			patch.object(cwh, "_delete_subscriptions_row", return_value=1) as mock_del_subs, \
			patch.object(cwh, "_delete_api_keys_for_user", return_value=0), \
			patch.object(cwh, "_delete_jobs_for_user", return_value=([], 0)), \
			patch.object(cwh, "_delete_urls_for_jobs", return_value=0), \
			patch.object(cwh, "_delete_templates_for_user", return_value=0), \
			patch.object(cwh, "_delete_webhooks_for_user", return_value=(0, [])), \
			patch.object(cwh, "_delete_webhook_deliveries_for_user", return_value=0):
			cwh._handle_user_deleted({"id": "user-2"})

		mock_stripe_sub.cancel.assert_not_called()
		mock_del_subs.assert_called_once_with("user-2")

	def test_already_canceled_stripe_subscription_is_tolerated(self):
		"""'No such subscription' from Stripe is swallowed; the cascade proceeds."""
		err = stripe.InvalidRequestError("No such subscription: sub_x", "subscription")
		# The source matches on `"No such subscription" in str(e)`; pin that the
		# installed stripe surfaces the message so this test cannot silently stop
		# exercising the tolerate branch on a stripe version bump.
		assert "No such subscription" in str(err)
		with patch.object(cwh, "get_subscription",
						   return_value={"stripe_subscription_id": "sub_x"}), \
			patch.object(cwh.stripe, "Subscription") as mock_stripe_sub, \
			patch.object(cwh, "_delete_subscriptions_row", return_value=1) as mock_del_subs, \
			patch.object(cwh, "_delete_api_keys_for_user", return_value=0), \
			patch.object(cwh, "_delete_jobs_for_user", return_value=([], 0)), \
			patch.object(cwh, "_delete_urls_for_jobs", return_value=0), \
			patch.object(cwh, "_delete_templates_for_user", return_value=0), \
			patch.object(cwh, "_delete_webhooks_for_user", return_value=(0, [])), \
			patch.object(cwh, "_delete_webhook_deliveries_for_user", return_value=0):
			mock_stripe_sub.cancel.side_effect = err
			# Must NOT raise
			cwh._handle_user_deleted({"id": "user-3"})

		mock_del_subs.assert_called_once_with("user-3")

	def test_other_stripe_error_reraises_before_any_db_delete(self):
		"""A non-'already canceled' Stripe error aborts the cascade (so the entry
		point rolls back dedup and Clerk retries); no DB rows are touched."""
		err = stripe.InvalidRequestError("Card declined or whatever", "subscription")
		# Guard the symmetric assumption: this message must NOT match the tolerate
		# substring, otherwise the test would be checking the wrong branch.
		assert "No such subscription" not in str(err)
		with patch.object(cwh, "get_subscription",
						   return_value={"stripe_subscription_id": "sub_y"}), \
			patch.object(cwh.stripe, "Subscription") as mock_stripe_sub, \
			patch.object(cwh, "_delete_subscriptions_row") as mock_del_subs:
			mock_stripe_sub.cancel.side_effect = err
			with pytest.raises(stripe.InvalidRequestError):
				cwh._handle_user_deleted({"id": "user-4"})

		mock_del_subs.assert_not_called()

	def test_threads_job_ids_and_webhook_ids_between_dependent_helpers(self):
		"""URLs are keyed by job_id and deliveries by webhook_id, so the ids
		collected by the jobs/webhooks deletes must flow into the next helper."""
		with patch.object(cwh, "get_subscription",
						   return_value={"stripe_subscription_id": ""}), \
			patch.object(cwh.stripe, "Subscription"), \
			patch.object(cwh, "_delete_subscriptions_row", return_value=1) as mock_subs, \
			patch.object(cwh, "_delete_api_keys_for_user", return_value=3) as mock_keys, \
			patch.object(cwh, "_delete_jobs_for_user",
						 return_value=(["j1", "j2"], 2)) as mock_jobs, \
			patch.object(cwh, "_delete_urls_for_jobs", return_value=5) as mock_urls, \
			patch.object(cwh, "_delete_templates_for_user", return_value=1) as mock_tpl, \
			patch.object(cwh, "_delete_webhooks_for_user",
						 return_value=(2, ["w1", "w2"])) as mock_wh, \
			patch.object(cwh, "_delete_webhook_deliveries_for_user", return_value=9) as mock_del:
			cwh._handle_user_deleted({"id": "user-5"})

		mock_subs.assert_called_once_with("user-5")
		mock_keys.assert_called_once_with("user-5")
		mock_jobs.assert_called_once_with("user-5")
		mock_tpl.assert_called_once_with("user-5")
		mock_wh.assert_called_once_with("user-5")
		mock_urls.assert_called_once_with(["j1", "j2"])
		mock_del.assert_called_once_with(["w1", "w2"])


# ─── Per-table deletion helpers ───────────────────────────────────────────────

@pytest.mark.unit
class TestPerTableHelpers:
	def test_delete_subscriptions_row_deletes_by_user_id_and_returns_1(self):
		mock_table = MagicMock()
		with patch.object(cwh, "get_table", return_value=mock_table):
			result = cwh._delete_subscriptions_row("user-a")
		assert result == 1
		mock_table.delete_item.assert_called_once_with(Key={"user_id": "user-a"})

	def test_delete_subscriptions_row_reraises_on_error(self):
		mock_table = MagicMock()
		mock_table.delete_item.side_effect = RuntimeError("dynamo down")
		with patch.object(cwh, "get_table", return_value=mock_table):
			with pytest.raises(RuntimeError):
				cwh._delete_subscriptions_row("user-a")

	def test_delete_api_keys_maps_items_to_keys_and_returns_count(self):
		items = [{"api_key_id": "k1"}, {"api_key_id": "k2"}]
		with patch.object(cwh, "get_table", return_value=MagicMock()), \
			patch.object(cwh, "_scan_gsi", return_value=items), \
			patch.object(cwh, "_batch_delete", return_value=2) as mock_batch:
			result = cwh._delete_api_keys_for_user("user-b")
		assert result == 2
		mock_batch.assert_called_once()
		# Second positional arg is the list of primary keys to delete
		assert mock_batch.call_args.args[1] == [{"api_key_id": "k1"}, {"api_key_id": "k2"}]

	def test_delete_jobs_returns_job_ids_and_count(self):
		items = [{"job_id": "j1"}, {"job_id": "j2"}]
		with patch.object(cwh, "get_table", return_value=MagicMock()), \
			patch.object(cwh, "_scan_filter_user", return_value=items), \
			patch.object(cwh, "_batch_delete", return_value=2) as mock_batch:
			job_ids, count = cwh._delete_jobs_for_user("user-c")
		assert job_ids == ["j1", "j2"]
		assert count == 2
		assert mock_batch.call_args.args[1] == [{"job_id": "j1"}, {"job_id": "j2"}]

	def test_delete_webhooks_returns_count_and_webhook_ids(self):
		items = [{"webhook_id": "w1"}, {"webhook_id": "w2"}]
		with patch.object(cwh, "get_table", return_value=MagicMock()), \
			patch.object(cwh, "_scan_filter_user", return_value=items), \
			patch.object(cwh, "_batch_delete", return_value=2):
			count, webhook_ids = cwh._delete_webhooks_for_user("user-d")
		assert count == 2
		assert webhook_ids == ["w1", "w2"]

	def test_delete_templates_maps_items_to_keys_and_returns_count(self):
		items = [{"template_id": "t1"}, {"template_id": "t2"}]
		with patch.object(cwh, "get_table", return_value=MagicMock()), \
			patch.object(cwh, "_scan_filter_user", return_value=items), \
			patch.object(cwh, "_batch_delete", return_value=2) as mock_batch:
			result = cwh._delete_templates_for_user("user-e")
		assert result == 2
		assert mock_batch.call_args.args[1] == [{"template_id": "t1"}, {"template_id": "t2"}]

	def test_delete_urls_for_empty_job_list_short_circuits_without_table(self):
		with patch.object(cwh, "get_table") as mock_get_table:
			assert cwh._delete_urls_for_jobs([]) == 0
		mock_get_table.assert_not_called()

	def test_delete_webhook_deliveries_for_empty_list_short_circuits(self):
		with patch.object(cwh, "get_table") as mock_get_table:
			assert cwh._delete_webhook_deliveries_for_user([]) == 0
		mock_get_table.assert_not_called()

	def test_delete_urls_for_jobs_queries_each_job_then_batch_deletes(self):
		mock_table = MagicMock()
		mock_table.query.return_value = {
			"Items": [{"job_id": "j1", "url": "https://a"}]
		}
		with patch.object(cwh, "get_table", return_value=mock_table), \
			patch.object(cwh, "_batch_delete", return_value=2) as mock_batch:
			result = cwh._delete_urls_for_jobs(["j1", "j2"])
		assert result == 2
		assert mock_table.query.call_count == 2  # one query per job_id
		assert mock_batch.call_args.args[1] == [
			{"job_id": "j1", "url": "https://a"},
			{"job_id": "j1", "url": "https://a"},
		]

	def test_delete_urls_for_jobs_paginates_within_a_single_job(self):
		"""The URLs helper has its own inline LastEvaluatedKey loop (separate from
		_scan_gsi); a job with multiple URL pages must resume from the prior key."""
		mock_table = MagicMock()
		mock_table.query.side_effect = [
			{"Items": [{"job_id": "j1", "url": "https://a"}],
			 "LastEvaluatedKey": {"job_id": "j1", "url": "https://a"}},
			{"Items": [{"job_id": "j1", "url": "https://b"}]},
		]
		with patch.object(cwh, "get_table", return_value=mock_table), \
			patch.object(cwh, "_batch_delete", return_value=2) as mock_batch:
			result = cwh._delete_urls_for_jobs(["j1"])
		assert result == 2
		assert mock_table.query.call_count == 2  # two pages for the one job
		assert mock_table.query.call_args_list[1].kwargs["ExclusiveStartKey"] == {
			"job_id": "j1", "url": "https://a"
		}
		assert mock_batch.call_args.args[1] == [
			{"job_id": "j1", "url": "https://a"},
			{"job_id": "j1", "url": "https://b"},
		]


# ─── Low-level helpers ────────────────────────────────────────────────────────

@pytest.mark.unit
class TestLowLevelHelpers:
	def test_batch_delete_empty_returns_zero_without_writer(self):
		mock_table = MagicMock()
		assert cwh._batch_delete(mock_table, []) == 0
		mock_table.batch_writer.assert_not_called()

	def test_batch_delete_chunks_at_twenty_five(self):
		mock_table = MagicMock()
		batch = mock_table.batch_writer.return_value.__enter__.return_value
		keys = [{"job_id": f"j{i}"} for i in range(30)]
		count = cwh._batch_delete(mock_table, keys)
		assert count == 30
		# 30 keys -> two chunks (25 + 5) -> two batch_writer() contexts
		assert mock_table.batch_writer.call_count == 2
		assert batch.delete_item.call_count == 30

	def test_scan_gsi_aggregates_paginated_results(self):
		mock_table = MagicMock()
		mock_table.query.side_effect = [
			{"Items": [{"id": 1}], "LastEvaluatedKey": {"id": 1}},
			{"Items": [{"id": 2}]},
		]
		items = cwh._scan_gsi(mock_table, "UserIdIndex", "user_id", "u1")
		assert items == [{"id": 1}, {"id": 2}]
		assert mock_table.query.call_count == 2
		first_kwargs = mock_table.query.call_args_list[0].kwargs
		assert first_kwargs["IndexName"] == "UserIdIndex"
		assert "user_id = :val" in first_kwargs["KeyConditionExpression"]
		# Second page must resume from the prior LastEvaluatedKey
		assert mock_table.query.call_args_list[1].kwargs["ExclusiveStartKey"] == {"id": 1}

	def test_scan_filter_user_aggregates_paginated_results(self):
		mock_table = MagicMock()
		mock_table.scan.side_effect = [
			{"Items": [{"user_id": "u1", "n": 1}], "LastEvaluatedKey": {"k": 1}},
			{"Items": [{"user_id": "u1", "n": 2}]},
		]
		items = cwh._scan_filter_user(mock_table, "u1")
		assert items == [{"user_id": "u1", "n": 1}, {"user_id": "u1", "n": 2}]
		assert mock_table.scan.call_count == 2
		first_kwargs = mock_table.scan.call_args_list[0].kwargs
		assert first_kwargs["FilterExpression"] == "user_id = :uid"
		assert first_kwargs["ExpressionAttributeValues"] == {":uid": "u1"}
		assert mock_table.scan.call_args_list[1].kwargs["ExclusiveStartKey"] == {"k": 1}

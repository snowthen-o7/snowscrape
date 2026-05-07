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

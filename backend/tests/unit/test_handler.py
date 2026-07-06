"""Unit tests for handler.py — the HTTP data-plane layer (issue #40, group 1).

handler.py (3703 lines, ~36 Lambda entrypoints) is the API surface real clients
hit but has had no dedicated test file: the lower-level logic (job_manager,
validators, utils, billing) is covered, yet the handler layer itself — auth
resolution, the billing status-code gate, the validation→400 mapping, the success
response shape, and CORS origin selection — was exercised only indirectly.

These are CHARACTERIZATION tests (no source change): they pin the CURRENT behavior
of `create_job_handler` and `get_cors_origin` so a future regression (an auth check
dropped, a 200 returned on a failure, a disallowed CORS origin reflected) fails
loudly. handler.py binds DynamoDB/S3/SQS resources and the CORS allow-set at import
time, so it is (re)imported fresh inside a moto context per test.

This is group 1 of the incremental plan in #40 (create_job_handler + the CORS
guard). The remaining handler groups (list/detail, lifecycle transitions,
download/preview) are deferred to follow-up cycles.
"""
import importlib
import json
import sys
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws


@pytest.fixture
def handler_mod(aws_credentials, mock_env_vars):
	"""Import handler.py fresh inside a moto context.

	handler.py binds the table handles, S3/SQS clients, and `_CORS_ALLOWED_ORIGINS`
	at module import, so it must be (re)imported with the env vars set and AWS faked.
	Reloading per test keeps those module globals isolated; the autouse
	`reset_connection_pool` fixture clears the cached boto resources around it.
	"""
	with mock_aws():
		import handler as handler_module
		importlib.reload(handler_module)
		yield handler_module


def _event(body=None, origin=None, include_body=True):
	"""Build a minimal API Gateway proxy event."""
	event = {'headers': {}}
	if origin is not None:
		event['headers']['origin'] = origin
	if include_body and body is not None:
		event['body'] = body if isinstance(body, str) else json.dumps(body)
	return event


# A patch bundle that lets every billing check pass, so a test can reach the
# create_job call without depending on the real subscriptions table / Stripe.
def _billing_all_allowed():
	return [
		patch('billing.get_subscription', return_value={'plan': 'pro', 'status': 'active'}),
		patch('billing.is_subscription_active', return_value=True),
		patch('billing.check_usage_quota',
			  return_value={'allowed': True, 'plan': 'pro', 'used': 0, 'limit': 25000}),
		patch('billing.check_concurrent_job_limit',
			  return_value={'allowed': True, 'plan': 'pro', 'active_jobs': 0, 'limit': 5}),
		patch('billing.check_feature_access', return_value={'allowed': True, 'plan': 'pro'}),
	]


@pytest.mark.unit
class TestGetCorsOrigin:
	"""`get_cors_origin` must reflect an allowed origin but NEVER reflect a
	disallowed one (it falls back to a configured origin instead). This is a
	security guard: reflecting an attacker-supplied Origin would defeat CORS."""

	def test_reflects_request_origin_when_allowed(self, handler_mod, monkeypatch):
		monkeypatch.setattr(handler_mod, '_CORS_ALLOWED_ORIGINS', {'http://localhost:3001'})
		event = _event(origin='http://localhost:3001')
		assert handler_mod.get_cors_origin(event) == 'http://localhost:3001'

	def test_does_not_reflect_disallowed_origin(self, handler_mod, monkeypatch):
		# Use a MULTI-element allow-set that does NOT contain the request origin, so
		# this is a real non-reflection check: the only way to satisfy both asserts
		# is for the membership branch to gate reflection (a function that blindly
		# echoed the request origin would fail `result in allowed`).
		allowed = {'http://app.example.com', 'http://admin.example.com'}
		monkeypatch.setattr(handler_mod, '_CORS_ALLOWED_ORIGINS', allowed)
		event = _event(origin='https://evil.example.com')
		result = handler_mod.get_cors_origin(event)
		assert result != 'https://evil.example.com'
		assert result in allowed

	def test_multi_origin_reflects_only_the_matching_one(self, handler_mod, monkeypatch):
		allowed = {'http://a.example.com', 'http://b.example.com'}
		monkeypatch.setattr(handler_mod, '_CORS_ALLOWED_ORIGINS', allowed)
		assert handler_mod.get_cors_origin(_event(origin='http://a.example.com')) == 'http://a.example.com'
		assert handler_mod.get_cors_origin(_event(origin='http://b.example.com')) == 'http://b.example.com'
		# An unknown origin is never reflected; the fallback is a configured one.
		fallback = handler_mod.get_cors_origin(_event(origin='http://c.example.com'))
		assert fallback in allowed

	def test_honors_capitalized_Origin_header_key(self, handler_mod, monkeypatch):
		monkeypatch.setattr(handler_mod, '_CORS_ALLOWED_ORIGINS', {'http://localhost:3001'})
		event = {'headers': {'Origin': 'http://localhost:3001'}}
		assert handler_mod.get_cors_origin(event) == 'http://localhost:3001'

	def test_no_event_returns_a_configured_origin(self, handler_mod, monkeypatch):
		allowed = {'http://localhost:3001'}
		monkeypatch.setattr(handler_mod, '_CORS_ALLOWED_ORIGINS', allowed)
		assert handler_mod.get_cors_origin(None) in allowed
		assert handler_mod.get_cors_origin({}) in allowed
		# Missing/empty headers also fall back, never raise.
		assert handler_mod.get_cors_origin({'headers': None}) in allowed


@pytest.mark.unit
class TestCreateJobHandlerAuth:
	"""Auth is resolved before anything else; both no-token and bad-token are 401."""

	def test_missing_token_returns_401(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value=None):
			resp = handler_mod.create_job_handler(_event(body={}), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'Unauthorized - No token provided'
		assert 'Access-Control-Allow-Origin' in resp['headers']

	def test_invalid_token_returns_401_with_the_error_message(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', side_effect=Exception('bad token')):
			resp = handler_mod.create_job_handler(_event(body={}), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'bad token'


@pytest.mark.unit
class TestCreateJobHandlerValidation:
	"""Validation (and body parsing) happen after auth, before billing."""

	def test_validation_error_returns_400(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'validate_job_data', side_effect=ValueError('bad field')):
			resp = handler_mod.create_job_handler(_event(body={}), lambda_context)
		assert resp['statusCode'] == 400
		assert json.loads(resp['body'])['message'].startswith('Validation error:')

	def test_malformed_json_body_returns_400(self, handler_mod, lambda_context):
		# json.JSONDecodeError subclasses ValueError, so a bad body maps to 400.
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'):
			resp = handler_mod.create_job_handler(_event(body='{not json', include_body=True), lambda_context)
		assert resp['statusCode'] == 400

	def test_missing_body_key_returns_500(self, handler_mod, lambda_context):
		# event['body'] is absent → KeyError → caught by the generic handler → 500.
		event = {'headers': {}}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'):
			resp = handler_mod.create_job_handler(event, lambda_context)
		assert resp['statusCode'] == 500
		assert json.loads(resp['body'])['message'] == 'Internal server error'


@pytest.mark.unit
class TestCreateJobHandlerBilling:
	"""The billing gate maps each limit to its own status code; an inactive
	subscription fails CLOSED with 402 before the job is ever created."""

	def test_inactive_subscription_returns_402(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'validate_job_data', MagicMock()), \
			 patch.object(handler_mod, 'create_job') as mock_create, \
			 patch('billing.get_subscription',
				   return_value={'plan': 'locked', 'status': 'no_subscription'}), \
			 patch('billing.is_subscription_active', return_value=False), \
			 patch('billing.check_usage_quota',
				   return_value={'allowed': True, 'plan': 'locked', 'used': 0, 'limit': 0}), \
			 patch('billing.check_concurrent_job_limit',
				   return_value={'allowed': True, 'plan': 'locked', 'active_jobs': 0, 'limit': 0}):
			# Quota/concurrency are allowed, so the ONLY path to 402 here is the
			# inactive-subscription gate firing first (fail-closed).
			resp = handler_mod.create_job_handler(_event(body={}), lambda_context)
		assert resp['statusCode'] == 402
		body = json.loads(resp['body'])
		assert body['message'] == 'Active subscription required'
		assert body['plan'] == 'locked'
		# The job is NOT created when the subscription gate fails closed.
		mock_create.assert_not_called()

	def test_over_page_quota_returns_402(self, handler_mod, lambda_context):
		patches = [
			patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
			patch.object(handler_mod, 'resolve_user_id', return_value='user-1'),
			patch.object(handler_mod, 'validate_job_data', MagicMock()),
			patch('billing.get_subscription', return_value={'plan': 'pro', 'status': 'active'}),
			patch('billing.is_subscription_active', return_value=True),
			patch('billing.check_usage_quota',
				  return_value={'allowed': False, 'plan': 'pro', 'used': 25000, 'limit': 25000}),
		]
		for p in patches:
			p.start()
		try:
			resp = handler_mod.create_job_handler(_event(body={}), lambda_context)
		finally:
			for p in patches:
				p.stop()
		assert resp['statusCode'] == 402
		assert json.loads(resp['body'])['message'] == 'Monthly page limit reached'

	def test_concurrent_limit_returns_429(self, handler_mod, lambda_context):
		patches = [
			patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
			patch.object(handler_mod, 'resolve_user_id', return_value='user-1'),
			patch.object(handler_mod, 'validate_job_data', MagicMock()),
			patch('billing.get_subscription', return_value={'plan': 'pro', 'status': 'active'}),
			patch('billing.is_subscription_active', return_value=True),
			patch('billing.check_usage_quota',
				  return_value={'allowed': True, 'plan': 'pro', 'used': 0, 'limit': 25000}),
			patch('billing.check_concurrent_job_limit',
				  return_value={'allowed': False, 'plan': 'pro', 'active_jobs': 5, 'limit': 5}),
		]
		for p in patches:
			p.start()
		try:
			resp = handler_mod.create_job_handler(_event(body={}), lambda_context)
		finally:
			for p in patches:
				p.stop()
		assert resp['statusCode'] == 429
		assert json.loads(resp['body'])['message'] == 'Concurrent job limit reached'

	def test_js_rendering_feature_gate_returns_403(self, handler_mod, lambda_context):
		# A premium feature (JS rendering) requested without access is a 403, a
		# distinct status from the 402 quota gates.
		patches = [
			patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
			patch.object(handler_mod, 'resolve_user_id', return_value='user-1'),
			patch.object(handler_mod, 'validate_job_data', MagicMock()),
			patch.object(handler_mod, 'create_job'),
			patch('billing.get_subscription', return_value={'plan': 'free', 'status': 'active'}),
			patch('billing.is_subscription_active', return_value=True),
			patch('billing.check_usage_quota',
				  return_value={'allowed': True, 'plan': 'free', 'used': 0, 'limit': 1000}),
			patch('billing.check_concurrent_job_limit',
				  return_value={'allowed': True, 'plan': 'free', 'active_jobs': 0, 'limit': 1}),
			patch('billing.check_feature_access', return_value={'allowed': False, 'plan': 'free'}),
		]
		started = [p.start() for p in patches]
		try:
			mock_create = started[3]
			resp = handler_mod.create_job_handler(
				_event(body={'render_config': {'enabled': True}}), lambda_context)
		finally:
			for p in patches:
				p.stop()
		assert resp['statusCode'] == 403
		assert json.loads(resp['body'])['message'] == 'JS rendering requires a Pro or higher plan'
		mock_create.assert_not_called()

	def test_billing_check_failure_is_fail_open(self, handler_mod, lambda_context):
		# A raising billing CHECK must NOT block job creation (fail-open on errors,
		# distinct from the fail-CLOSED inactive-subscription path above). This hits
		# the `except Exception as billing_err` branch.
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'validate_job_data', MagicMock()), \
			 patch.object(handler_mod, 'create_job', return_value='job-fo') as mock_create, \
			 patch('billing.get_subscription', side_effect=RuntimeError('billing down')):
			resp = handler_mod.create_job_handler(_event(body={}), lambda_context)
		assert resp['statusCode'] == 201
		mock_create.assert_called_once()

	def test_billing_module_absent_is_fail_open(self, handler_mod, lambda_context):
		# If the billing module itself is unavailable, the `from billing import (...)`
		# raises ImportError and enforcement is SKIPPED entirely (hits the
		# `except ImportError` branch). Job creation still succeeds.
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'validate_job_data', MagicMock()), \
			 patch.object(handler_mod, 'create_job', return_value='job-noimp') as mock_create, \
			 patch.dict(sys.modules, {'billing': None}):
			resp = handler_mod.create_job_handler(_event(body={}), lambda_context)
		assert resp['statusCode'] == 201
		mock_create.assert_called_once()


@pytest.mark.unit
class TestCreateJobHandlerSuccess:
	"""The happy path and the create-failure path."""

	def test_happy_path_returns_201_and_injects_user_id(self, handler_mod, lambda_context):
		patches = _billing_all_allowed() + [
			patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
			patch.object(handler_mod, 'resolve_user_id', return_value='user-1'),
			patch.object(handler_mod, 'validate_job_data', MagicMock()),
			patch.object(handler_mod, 'create_job', return_value='job-abc'),
		]
		started = [p.start() for p in patches]
		try:
			mock_create = started[-1]  # the create_job patcher's MagicMock
			resp = handler_mod.create_job_handler(_event(body={'name': 'My Job'}), lambda_context)
		finally:
			for p in patches:
				p.stop()
		assert resp['statusCode'] == 201
		body = json.loads(resp['body'])
		assert body['job_id'] == 'job-abc'
		assert body['message'] == 'Job created successfully'
		# Success response carries the credentialed-CORS headers.
		assert resp['headers']['Access-Control-Allow-Credentials'] is True
		assert 'Access-Control-Allow-Origin' in resp['headers']
		# The handler injects the resolved user_id into the job data before creating.
		mock_create.assert_called_once()
		created_arg = mock_create.call_args[0][0]
		assert created_arg['user_id'] == 'user-1'

	def test_create_job_returns_falsy_yields_500(self, handler_mod, lambda_context):
		patches = _billing_all_allowed() + [
			patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
			patch.object(handler_mod, 'resolve_user_id', return_value='user-1'),
			patch.object(handler_mod, 'validate_job_data', MagicMock()),
			patch.object(handler_mod, 'create_job', return_value=None),
		]
		for p in patches:
			p.start()
		try:
			resp = handler_mod.create_job_handler(_event(body={}), lambda_context)
		finally:
			for p in patches:
				p.stop()
		assert resp['statusCode'] == 500
		assert json.loads(resp['body'])['message'] == 'Failed to create job'

"""API-key authentication on the webhook management handlers (issue #11).

The webhook CRUD handlers (create/list/delete/test) authenticated only via
`validate_clerk_token`, so a programmatic caller presenting a SnowScrape API key
(`sk_live_...` Bearer) was rejected even though the job/data-plane endpoints
already accept API keys through `resolve_user_id`. These tests pin that all four
webhook handlers now resolve the caller via `resolve_user_id` (the API-key-aware
path) and return 401 on an invalid credential, matching the job handlers'
contract.

handler.py binds its table handles at import, so it is reimported fresh inside a
moto context per test, and `webhook_table` is patched to a MagicMock to keep
these focused on the auth wiring (not DynamoDB). `validate_clerk_token` is
patched to return a DIFFERENT user id than `resolve_user_id`, so a handler still
on the old auth path would persist/scope the wrong user and fail loudly.
"""
import importlib
import json
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws


@pytest.fixture
def handler_mod(aws_credentials, mock_env_vars):
	"""Import handler.py fresh inside a moto context (it binds table handles at import)."""
	with mock_aws():
		import handler as handler_module
		importlib.reload(handler_module)
		yield handler_module


def _event(body=None, path_params=None):
	"""Build a minimal API Gateway proxy event."""
	event = {'headers': {}}
	if body is not None:
		event['body'] = body if isinstance(body, str) else json.dumps(body)
	if path_params is not None:
		event['pathParameters'] = path_params
	return event


WEBHOOK_HANDLERS = [
	'create_webhook_handler',
	'list_webhooks_handler',
	'delete_webhook_handler',
	'test_webhook_handler',
]


@pytest.mark.unit
class TestWebhookHandlersAcceptApiKey:
	"""Each webhook handler must resolve the caller via resolve_user_id (the
	API-key-aware path), NOT validate_clerk_token, so an sk_live_ Bearer works and
	the row is scoped to the resolved user."""

	def test_create_webhook_uses_resolved_user(self, handler_mod, lambda_context):
		wh_table = MagicMock()
		with patch.object(handler_mod, 'extract_token_from_event', return_value='sk_live_abc'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1') as mock_resolve, \
			 patch.object(handler_mod, 'validate_clerk_token', return_value={'sub': 'CLERK-WRONG'}), \
			 patch.object(handler_mod, 'webhook_table', wh_table):
			resp = handler_mod.create_webhook_handler(
				_event({'url': 'https://example.com/hook', 'events': ['job.completed']}),
				lambda_context,
			)
		assert resp['statusCode'] == 201
		mock_resolve.assert_called_once_with('sk_live_abc')
		_, kwargs = wh_table.put_item.call_args
		assert kwargs['Item']['user_id'] == 'user-1'

	def test_list_webhooks_uses_resolved_user(self, handler_mod, lambda_context):
		wh_table = MagicMock()
		wh_table.query.return_value = {'Items': []}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='sk_live_abc'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1') as mock_resolve, \
			 patch.object(handler_mod, 'validate_clerk_token', return_value={'sub': 'CLERK-WRONG'}), \
			 patch.object(handler_mod, 'webhook_table', wh_table):
			resp = handler_mod.list_webhooks_handler(_event(), lambda_context)
		assert resp['statusCode'] == 200
		mock_resolve.assert_called_once_with('sk_live_abc')
		_, kwargs = wh_table.query.call_args
		assert kwargs['ExpressionAttributeValues'][':user_id'] == 'user-1'

	def test_delete_webhook_uses_resolved_user(self, handler_mod, lambda_context):
		wh_table = MagicMock()
		wh_table.get_item.return_value = {'Item': {'webhook_id': 'wh-1', 'user_id': 'user-1'}}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='sk_live_abc'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1') as mock_resolve, \
			 patch.object(handler_mod, 'validate_clerk_token', return_value={'sub': 'CLERK-WRONG'}), \
			 patch.object(handler_mod, 'webhook_table', wh_table):
			resp = handler_mod.delete_webhook_handler(
				_event(path_params={'webhook_id': 'wh-1'}), lambda_context,
			)
		assert resp['statusCode'] == 200
		mock_resolve.assert_called_once_with('sk_live_abc')
		wh_table.update_item.assert_called_once()

	def test_test_webhook_uses_resolved_user(self, handler_mod, lambda_context):
		wh_table = MagicMock()
		wh_table.get_item.return_value = {'Item': {'webhook_id': 'wh-1', 'user_id': 'user-1'}}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='sk_live_abc'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1') as mock_resolve, \
			 patch.object(handler_mod, 'validate_clerk_token', return_value={'sub': 'CLERK-WRONG'}), \
			 patch.object(handler_mod, 'webhook_table', wh_table), \
			 patch.object(handler_mod.WebhookDispatcher, 'dispatch_event', return_value=None) as mock_dispatch:
			resp = handler_mod.test_webhook_handler(
				_event(path_params={'webhook_id': 'wh-1'}), lambda_context,
			)
		assert resp['statusCode'] == 200
		mock_resolve.assert_called_once_with('sk_live_abc')
		# dispatched under the resolved user, not the Clerk-shaped one
		assert mock_dispatch.call_args.kwargs['user_id'] == 'user-1'


@pytest.mark.unit
class TestWebhookHandlersRejectInvalidCredential:
	"""An invalid credential must 401 (resolve_user_id raising), surfacing the
	error message, rather than falling through to a 500."""

	@pytest.mark.parametrize('handler_name', WEBHOOK_HANDLERS)
	def test_invalid_credential_returns_401(self, handler_mod, lambda_context, handler_name):
		evt = _event(
			{'url': 'https://x', 'events': ['job.completed']},
			path_params={'webhook_id': 'wh-1'},
		)
		with patch.object(handler_mod, 'extract_token_from_event', return_value='sk_live_bad'), \
			 patch.object(handler_mod, 'resolve_user_id', side_effect=Exception('Invalid API key')), \
			 patch.object(handler_mod, 'webhook_table', MagicMock()):
			resp = getattr(handler_mod, handler_name)(evt, lambda_context)
		assert resp['statusCode'] == 401
		assert 'Invalid API key' in resp['body']

	@pytest.mark.parametrize('handler_name', WEBHOOK_HANDLERS)
	def test_missing_token_returns_401(self, handler_mod, lambda_context, handler_name):
		with patch.object(handler_mod, 'extract_token_from_event', return_value=None):
			resp = getattr(handler_mod, handler_name)(_event(), lambda_context)
		assert resp['statusCode'] == 401

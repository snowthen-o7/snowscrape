"""5xx responses must not leak raw exception text in the body (issue #55).

Across handler.py the exception handlers used to put raw ``str(e)`` into an
``error`` field of the 5xx response body, in several spellings:
``"error": str(e)`` (the dominant ~20 sites), ``'error': str(e)`` (health
check), and ``'error': f'Internal server error: {str(e)}'`` (preview-url). On an
internal exception (boto/DynamoDB errors, KeyErrors, conversion failures)
``str(e)`` can disclose implementation detail (table/resource ARNs, internal
field names) to the caller, and with the webhook/job management endpoints now
accepting ``sk_live_`` API keys (#11) those bodies reach programmatic callers,
not just the dashboard (CWE-209). The health check is the most exposed: it is
unauthenticated.

The full exception is still logged server-side (every site calls
``log_exception``/``logger.warning``), so detail is preserved in CloudWatch;
only the client-facing body is reduced to a stable, generic message.

Guards:

* a behavioral test forcing the webhook create handler into its ``except`` path
  (a representative ``"error": str(e)`` site);
* a behavioral test forcing the unauthenticated health check into a degraded
  503 (the ``'error': str(e)`` site), asserting the failing dependency is still
  named but its raw error is gone; and
* a static guard asserting no ``"error": str(e)`` (the canonical double-quoted
  500-body form every handler uses) and no f-string ``error`` value carrying
  ``str(e)`` remain, so a copy-pasted 5xx handler cannot reintroduce the leak.
  (A few ``'error': str(e)`` occurrences remain by design: a 400 SFTP-validation
  message, a proxy-health list item, and a WebSocket payload, none of which are
  5xx HTTP response bodies.)
"""
import importlib
import json
import re
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
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


# A string an internal exception might carry that must never reach the client.
SENSITIVE = 'arn:aws:dynamodb:us-east-2:123456789012:table/SnowScrape-webhooks-prod'


@pytest.mark.unit
class TestFiveXXDoesNotLeakExceptionText:
	"""A forced internal error in a representative handler must return a generic
	5xx body with no raw exception text, while still logging the detail."""

	def test_create_webhook_internal_error_is_redacted(self, handler_mod, lambda_context):
		wh_table = MagicMock()
		# The persist step raises a boto-shaped error carrying a sensitive ARN.
		wh_table.put_item.side_effect = Exception(SENSITIVE)
		with patch.object(handler_mod, 'extract_token_from_event', return_value='sk_live_abc'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'webhook_table', wh_table), \
			 patch.object(handler_mod, 'log_exception') as mock_log:
			resp = handler_mod.create_webhook_handler(
				_event({'url': 'https://example.com/hook', 'events': ['job.completed']}),
				lambda_context,
			)

		assert resp['statusCode'] == 500
		# The sensitive exception text must not appear anywhere in the client body.
		assert SENSITIVE not in resp['body']
		body = json.loads(resp['body'])
		# The stable generic message is preserved; no 'error' detail key is present.
		assert body == {'message': 'Failed to create webhook'}
		# The full exception is still logged server-side (detail preserved).
		mock_log.assert_called_once()
		assert mock_log.call_args.args[2] is wh_table.put_item.side_effect

	def test_health_check_degraded_does_not_leak_dependency_error(self, handler_mod, lambda_context):
		# Force the DynamoDB connectivity probe to raise a sensitive boto error.
		failing_table = MagicMock()
		type(failing_table).table_status = PropertyMock(side_effect=Exception(SENSITIVE))
		with patch.object(handler_mod, 'job_table', failing_table), \
			 patch.object(handler_mod, 'observatory', MagicMock()):
			resp = handler_mod.health_check_handler(_event(), lambda_context)

		# A failed dependency degrades the service to a 503.
		assert resp['statusCode'] == 503
		# The raw exception text must not reach the (unauthenticated) caller.
		assert SENSITIVE not in resp['body']
		body = json.loads(resp['body'])
		# The failing dependency is still identified by name + status, just no raw error.
		assert body['checks']['dynamodb']['status'] == 'unhealthy'
		assert 'error' not in body['checks']['dynamodb']


@pytest.mark.unit
class TestNoRawExceptionInAnyFiveXXBody:
	"""Static guard over the whole handler so the 5xx bodies stay redacted and a
	copy-pasted handler cannot reintroduce raw exception text in a 5xx body."""

	def test_handler_source_has_no_double_quoted_error_str_e(self):
		# The canonical 500-body form every handler uses is double-quoted.
		source = self._source()
		assert '"error": str(e)' not in source, (
			'A 5xx response body still echoes raw exception text (CWE-209, #55). '
			'Return a generic message and log the exception server-side instead.'
		)

	def test_handler_source_has_no_fstring_error_carrying_str_e(self):
		# Catch the f-string spelling, e.g. 'error': f'Internal server error: {str(e)}'.
		source = self._source()
		assert not re.search(r"error['\"]?\s*:\s*f['\"][^'\"]*str\(e\)", source), (
			'A 5xx response body still interpolates raw exception text into an '
			'error message (CWE-209, #55). Use a stable generic message instead.'
		)

	@staticmethod
	def _source():
		handler_path = Path(__file__).resolve().parents[2] / 'handler.py'
		return handler_path.read_text(encoding='utf-8')

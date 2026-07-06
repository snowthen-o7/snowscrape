"""Unit tests for handler.py job-lifecycle transitions (issue #40, group 3).

Group 1 (test_handler.py) pinned `create_job_handler` + the CORS guard; group 2
(test_handler_reads.py) pinned the read surface. This file covers the WRITE/lifecycle
transitions a client fires to mutate a job:

  - delete_job_handler   (delete + cache invalidation)
  - pause_job_handler    (pause)
  - cancel_job_handler   (cancel, with a success/failure branch)
  - refresh_job_handler  (re-fetch the job's URL set)
  - resume_job_handler   (resume)
  - update_job_handler   (validate + update + cache invalidation)

These are CHARACTERIZATION tests (no source change): they pin the CURRENT behavior so
a future regression fails loudly. Every one of these six handlers shares the SAME
auth + ownership preamble, and that preamble is the load-bearing SECURITY contract:
a mutation must (a) require a token, (b) 404 a missing job, and (c) only ever act on a
job the caller OWNS. The ownership 403 tests do NOT mock `verify_resource_ownership`:
they hand the handler a job dict whose `user_id` differs from the resolved caller, so
the REAL `utils.verify_resource_ownership` (raises PermissionError on mismatch) is
genuinely exercised, and each test also asserts the downstream mutator is NEVER called
once ownership fails. A regression that dropped a guard would let one user delete/
pause/cancel/edit another user's job, which is exactly what these pin against.

handler.py binds its DynamoDB/S3/SQS resources and the CORS allow-set at import, so it
is (re)imported fresh inside a moto context per test (the `handler_mod` fixture). The
mutators (`delete_job`/`pause_job`/`cancel_job`/`refresh_job`/`resume_job`/`update_job`),
the cache helpers (`cache_delete`), `validate_job_data`, and the auth helpers are all
`from ... import`ed into handler's namespace, so they are patched as attributes of the
reloaded module.

NOTE (deliberate characterization, not a recommendation): unlike `create_job_handler`
(which wraps `validate_job_data` + the body parse in try/except and maps a ValueError to
400), `update_job_handler` does NOT guard `json.loads(event['body'])` or
`validate_job_data`, so a malformed body or a validation failure PROPAGATES out of the
handler rather than returning 400. That asymmetry is pinned below so a future change is a
conscious one.
"""
import importlib
import json
import pytest
from unittest.mock import patch
from moto import mock_aws


@pytest.fixture
def handler_mod(aws_credentials, mock_env_vars):
	"""Import handler.py fresh inside a moto context (see module docstring)."""
	with mock_aws():
		import handler as handler_module
		importlib.reload(handler_module)
		yield handler_module


def _event(origin=None, path_params=None, body=None):
	"""Build a minimal API Gateway proxy event for a lifecycle endpoint."""
	event = {'headers': {}}
	if origin is not None:
		event['headers']['origin'] = origin
	if path_params is not None:
		event['pathParameters'] = path_params
	if body is not None:
		event['body'] = body
	return event


def _path(job_id='job-1'):
	return _event(path_params={'job_id': job_id})


# Every lifecycle handler and the job_manager mutator it ultimately calls. Used to
# parametrize the shared auth + ownership preamble so a guard cannot silently regress
# in just one of the six handlers.
LIFECYCLE = [
	('delete_job_handler', 'delete_job'),
	('pause_job_handler', 'pause_job'),
	('cancel_job_handler', 'cancel_job'),
	('refresh_job_handler', 'refresh_job'),
	('resume_job_handler', 'resume_job'),
	('update_job_handler', 'update_job'),
]


# ---------------------------------------------------------------------------
# Shared auth + ownership preamble (all six handlers)
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.parametrize('handler_name,mutator', LIFECYCLE)
class TestLifecyclePreamble:
	def test_missing_token_returns_401(self, handler_mod, lambda_context, handler_name, mutator):
		handler = getattr(handler_mod, handler_name)
		with patch.object(handler_mod, 'extract_token_from_event', return_value=None), \
			 patch.object(handler_mod, mutator) as mock_mutator:
			resp = handler(_path(), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'Unauthorized - No token provided'
		assert 'Access-Control-Allow-Origin' in resp['headers']
		mock_mutator.assert_not_called()

	def test_invalid_token_returns_401_with_message(self, handler_mod, lambda_context, handler_name, mutator):
		handler = getattr(handler_mod, handler_name)
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', side_effect=Exception('bad token')), \
			 patch.object(handler_mod, mutator) as mock_mutator:
			resp = handler(_path(), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'bad token'
		mock_mutator.assert_not_called()

	def test_job_not_found_returns_404(self, handler_mod, lambda_context, handler_name, mutator):
		handler = getattr(handler_mod, handler_name)
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=None), \
			 patch.object(handler_mod, mutator) as mock_mutator:
			resp = handler(_path(), lambda_context)
		assert resp['statusCode'] == 404
		assert json.loads(resp['body'])['message'] == 'Job not found'
		mock_mutator.assert_not_called()

	def test_foreign_owner_returns_403(self, handler_mod, lambda_context, handler_name, mutator):
		# REAL verify_resource_ownership: a job owned by user-2 is forbidden to user-1,
		# and the mutator is never reached. This is the cross-user-mutation guard.
		handler = getattr(handler_mod, handler_name)
		foreign = {'job_id': 'job-1', 'user_id': 'user-2'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=foreign), \
			 patch.object(handler_mod, mutator) as mock_mutator:
			resp = handler(_path(), lambda_context)
		assert resp['statusCode'] == 403
		assert 'permission' in json.loads(resp['body'])['message'].lower()
		mock_mutator.assert_not_called()


# ---------------------------------------------------------------------------
# delete_job_handler — success path + cache invalidation
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestDeleteJobHandler:
	def test_owner_delete_succeeds_and_invalidates_cache(self, handler_mod, lambda_context):
		owner = {'job_id': 'job-1', 'user_id': 'user-1'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=owner), \
			 patch.object(handler_mod, 'delete_job') as mock_delete, \
			 patch.object(handler_mod, 'cache_delete') as mock_cache_delete:
			resp = handler_mod.delete_job_handler(_path(), lambda_context)
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		assert body['message'] == 'Job deleted successfully'
		assert body['job_id'] == 'job-1'
		mock_delete.assert_called_once_with('job-1')
		# Both the per-job and the user's job-list cache entries are purged.
		deleted_keys = [c.args[0] for c in mock_cache_delete.call_args_list]
		assert deleted_keys == ['job:job-1', 'jobs:user-1']
		assert resp['headers']['Access-Control-Allow-Credentials'] is True


# ---------------------------------------------------------------------------
# pause / refresh / resume — identical success shape (one mutator, no cache work)
# ---------------------------------------------------------------------------
@pytest.mark.unit
@pytest.mark.parametrize('handler_name,mutator,message', [
	('pause_job_handler', 'pause_job', 'Job paused successfully'),
	('refresh_job_handler', 'refresh_job', 'Job refreshed successfully'),
	('resume_job_handler', 'resume_job', 'Job resumed successfully'),
])
class TestSimpleTransitions:
	def test_owner_transition_succeeds(self, handler_mod, lambda_context, handler_name, mutator, message):
		handler = getattr(handler_mod, handler_name)
		owner = {'job_id': 'job-1', 'user_id': 'user-1'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=owner), \
			 patch.object(handler_mod, mutator) as mock_mutator:
			resp = handler(_path(), lambda_context)
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		assert body['message'] == message
		assert body['job_id'] == 'job-1'
		mock_mutator.assert_called_once_with('job-1')
		assert resp['headers']['Access-Control-Allow-Credentials'] is True


# ---------------------------------------------------------------------------
# cancel_job_handler — success vs. failure branch on cancel_job's return value
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestCancelJobHandler:
	def test_cancel_truthy_returns_200(self, handler_mod, lambda_context):
		owner = {'job_id': 'job-1', 'user_id': 'user-1'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=owner), \
			 patch.object(handler_mod, 'cancel_job', return_value=True) as mock_cancel:
			resp = handler_mod.cancel_job_handler(_path(), lambda_context)
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		assert body['message'] == 'Job cancelled successfully'
		assert body['job_id'] == 'job-1'
		mock_cancel.assert_called_once_with('job-1')
		assert resp['headers']['Access-Control-Allow-Credentials'] is True

	def test_cancel_falsy_returns_500(self, handler_mod, lambda_context):
		# A falsy cancel_job result is the documented failure branch: 500 with the
		# job_id echoed, and (characterization) it still carries the credentialed
		# CORS headers like the success branch.
		owner = {'job_id': 'job-1', 'user_id': 'user-1'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=owner), \
			 patch.object(handler_mod, 'cancel_job', return_value=False):
			resp = handler_mod.cancel_job_handler(_path(), lambda_context)
		assert resp['statusCode'] == 500
		body = json.loads(resp['body'])
		assert body['message'] == 'Failed to cancel job'
		assert body['job_id'] == 'job-1'
		assert resp['headers']['Access-Control-Allow-Credentials'] is True


# ---------------------------------------------------------------------------
# update_job_handler — validate + update + cache invalidation, and the
# deliberate NON-guarding of body parse / validation (see module docstring)
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestUpdateJobHandler:
	def test_owner_update_validates_persists_and_invalidates_cache(self, handler_mod, lambda_context):
		owner = {'job_id': 'job-1', 'user_id': 'user-1'}
		new_data = {'name': 'renamed', 'urls': ['https://example.com']}
		event = _event(path_params={'job_id': 'job-1'}, body=json.dumps(new_data))
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=owner), \
			 patch.object(handler_mod, 'validate_job_data') as mock_validate, \
			 patch.object(handler_mod, 'update_job') as mock_update, \
			 patch.object(handler_mod, 'cache_delete') as mock_cache_delete:
			resp = handler_mod.update_job_handler(event, lambda_context)
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		assert body['message'] == 'Job updated successfully'
		assert body['job_id'] == 'job-1'
		# The parsed body is validated, then persisted under the path's job_id.
		mock_validate.assert_called_once_with(new_data)
		mock_update.assert_called_once_with('job-1', new_data)
		deleted_keys = [c.args[0] for c in mock_cache_delete.call_args_list]
		assert deleted_keys == ['job:job-1', 'jobs:user-1']
		assert resp['headers']['Access-Control-Allow-Credentials'] is True

	def test_validation_error_propagates_not_mapped_to_400(self, handler_mod, lambda_context):
		# Contrast with create_job_handler: update does NOT catch validate_job_data,
		# so a ValueError propagates out of the handler (no 400 mapping), and update_job
		# is never reached.
		owner = {'job_id': 'job-1', 'user_id': 'user-1'}
		event = _event(path_params={'job_id': 'job-1'}, body=json.dumps({'bad': True}))
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=owner), \
			 patch.object(handler_mod, 'validate_job_data', side_effect=ValueError('bad job')), \
			 patch.object(handler_mod, 'update_job') as mock_update:
			with pytest.raises(ValueError, match='bad job'):
				handler_mod.update_job_handler(event, lambda_context)
		mock_update.assert_not_called()

	def test_malformed_body_propagates(self, handler_mod, lambda_context):
		# json.loads(event['body']) is also unguarded: a malformed body raises
		# (JSONDecodeError subclasses ValueError) after the ownership check passes.
		owner = {'job_id': 'job-1', 'user_id': 'user-1'}
		event = _event(path_params={'job_id': 'job-1'}, body='not-json')
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=owner), \
			 patch.object(handler_mod, 'validate_job_data') as mock_validate, \
			 patch.object(handler_mod, 'update_job') as mock_update:
			with pytest.raises(ValueError):
				handler_mod.update_job_handler(event, lambda_context)
		mock_validate.assert_not_called()
		mock_update.assert_not_called()

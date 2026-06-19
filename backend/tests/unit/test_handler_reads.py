"""Unit tests for handler.py read surface — the job list/detail endpoints (issue #40, group 2).

Group 1 (test_handler.py) pinned `create_job_handler` + the CORS guard. This file
covers the READ data-plane real clients hit on every dashboard load:

  - get_all_job_statuses_handler  (paginated list, user-scoped)
  - get_job_details_handler        (single job, read-through cache)
  - get_crawl_handler              (one crawl under a job)
  - get_job_crawls_handler         (all crawls under a job)

These are CHARACTERIZATION tests (no source change): they pin the CURRENT behavior
so a future regression fails loudly. The load-bearing contracts here are SECURITY
boundaries — every read must (a) require a token, and (b) only ever return data the
caller owns. The list endpoint enforces this by filtering `get_all_jobs` results to
the caller's `user_id`; the detail/crawl endpoints enforce it via the REAL
`verify_resource_ownership` (these tests do NOT mock it — they hand the handler job
dicts whose `user_id` matches or differs from the caller, so the ownership check is
genuinely exercised, not stubbed into a tautology). A regression that dropped either
guard would leak another user's jobs/crawls and is exactly what these pin against.

handler.py binds its DynamoDB/S3/SQS resources and the CORS allow-set at import, so
it is (re)imported fresh inside a moto context per test (the `handler_mod` fixture);
the data-access helpers (`get_all_jobs`/`get_job`/`get_crawl`/`get_job_crawls`/
`cache_get`/`cache_set`) and auth helpers are `from ... import`ed into handler's
namespace, so they are patched as attributes of the reloaded module.
"""
import base64
import importlib
import json
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws


@pytest.fixture
def handler_mod(aws_credentials, mock_env_vars):
	"""Import handler.py fresh inside a moto context (see module docstring)."""
	with mock_aws():
		import handler as handler_module
		importlib.reload(handler_module)
		yield handler_module


def _event(origin=None, path_params=None, query_params=None):
	"""Build a minimal API Gateway proxy event for a read endpoint."""
	event = {'headers': {}}
	if origin is not None:
		event['headers']['origin'] = origin
	if path_params is not None:
		event['pathParameters'] = path_params
	if query_params is not None:
		event['queryStringParameters'] = query_params
	return event


def _authed(handler_mod, user_id='user-1'):
	"""Patchers that make auth resolve to `user_id`. Use inside a with/ExitStack."""
	return [
		patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
		patch.object(handler_mod, 'resolve_user_id', return_value=user_id),
	]


# ---------------------------------------------------------------------------
# get_all_job_statuses_handler — paginated, user-scoped list
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestGetAllJobStatusesHandlerAuth:
	def test_missing_token_returns_401(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value=None):
			resp = handler_mod.get_all_job_statuses_handler(_event(), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'Unauthorized - No token provided'
		assert 'Access-Control-Allow-Origin' in resp['headers']

	def test_invalid_token_returns_401_with_message(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', side_effect=Exception('bad token')):
			resp = handler_mod.get_all_job_statuses_handler(_event(), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'bad token'


@pytest.mark.unit
class TestGetAllJobStatusesHandlerScoping:
	"""The defining security contract: only the caller's own jobs are returned."""

	def test_filters_to_only_the_callers_jobs(self, handler_mod, lambda_context):
		# get_all_jobs returns a page mixing two users; the handler must drop the
		# foreign user's rows. A regression removing the filter would leak them.
		page = {'items': [
			{'job_id': 'a', 'user_id': 'user-1'},
			{'job_id': 'b', 'user_id': 'user-2'},
			{'job_id': 'c', 'user_id': 'user-1'},
		]}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_all_jobs', return_value=page):
			resp = handler_mod.get_all_job_statuses_handler(_event(), lambda_context)
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		assert [j['job_id'] for j in body['jobs']] == ['a', 'c']
		assert body['count'] == 2
		# Success carries the credentialed-CORS headers.
		assert resp['headers']['Access-Control-Allow-Credentials'] is True

	def test_no_matching_jobs_returns_empty_list(self, handler_mod, lambda_context):
		page = {'items': [{'job_id': 'b', 'user_id': 'user-2'}]}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_all_jobs', return_value=page):
			resp = handler_mod.get_all_job_statuses_handler(_event(), lambda_context)
		body = json.loads(resp['body'])
		assert body['jobs'] == []
		assert body['count'] == 0


@pytest.mark.unit
class TestGetAllJobStatusesHandlerPagination:
	def test_default_limit_is_50(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_all_jobs', return_value={'items': []}) as mock_all:
			handler_mod.get_all_job_statuses_handler(_event(), lambda_context)
		assert mock_all.call_args.kwargs['limit'] == 50
		assert mock_all.call_args.kwargs['last_evaluated_key'] is None

	def test_limit_is_capped_at_100(self, handler_mod, lambda_context):
		# A caller asking for 500 is clamped to the 100-item server cap.
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_all_jobs', return_value={'items': []}) as mock_all:
			handler_mod.get_all_job_statuses_handler(
				_event(query_params={'limit': '500'}), lambda_context)
		assert mock_all.call_args.kwargs['limit'] == 100

	def test_last_key_round_trips_when_more_pages_exist(self, handler_mod, lambda_context):
		# When get_all_jobs reports a continuation key, the handler base64(JSON)-
		# encodes it into response last_key; decoding must recover the exact key.
		next_key = {'job_id': {'S': 'z'}}
		page = {'items': [], 'last_evaluated_key': next_key}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_all_jobs', return_value=page):
			resp = handler_mod.get_all_job_statuses_handler(_event(), lambda_context)
		body = json.loads(resp['body'])
		assert 'last_key' in body
		decoded = json.loads(base64.b64decode(body['last_key']))
		assert decoded == next_key

	def test_no_last_key_when_no_more_pages(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_all_jobs', return_value={'items': []}):
			resp = handler_mod.get_all_job_statuses_handler(_event(), lambda_context)
		assert 'last_key' not in json.loads(resp['body'])

	def test_valid_incoming_last_key_is_decoded_and_forwarded(self, handler_mod, lambda_context):
		incoming = {'job_id': {'S': 'cursor'}}
		encoded = base64.b64encode(json.dumps(incoming).encode()).decode()
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_all_jobs', return_value={'items': []}) as mock_all:
			handler_mod.get_all_job_statuses_handler(
				_event(query_params={'last_key': encoded}), lambda_context)
		assert mock_all.call_args.kwargs['last_evaluated_key'] == incoming

	def test_invalid_last_key_is_swallowed_and_treated_as_none(self, handler_mod, lambda_context):
		# A malformed pagination cursor must NOT 500 the read; it is logged and the
		# query proceeds from the start (last_evaluated_key=None).
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_all_jobs', return_value={'items': []}) as mock_all:
			resp = handler_mod.get_all_job_statuses_handler(
				_event(query_params={'last_key': 'not-valid-base64-json!!'}), lambda_context)
		assert resp['statusCode'] == 200
		assert mock_all.call_args.kwargs['last_evaluated_key'] is None


@pytest.mark.unit
class TestGetAllJobStatusesHandlerErrors:
	def test_get_all_jobs_raising_returns_500(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_all_jobs', side_effect=RuntimeError('ddb down')):
			resp = handler_mod.get_all_job_statuses_handler(_event(), lambda_context)
		assert resp['statusCode'] == 500
		assert json.loads(resp['body'])['message'] == 'Internal server error'


# ---------------------------------------------------------------------------
# get_job_details_handler — single job, read-through cache + ownership
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestGetJobDetailsHandler:
	def _path(self, job_id='job-1'):
		return _event(path_params={'job_id': job_id})

	def test_missing_token_returns_401(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value=None):
			resp = handler_mod.get_job_details_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 401

	def test_invalid_token_returns_401_with_message(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', side_effect=Exception('nope')):
			resp = handler_mod.get_job_details_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'nope'

	def test_cache_hit_skips_get_job(self, handler_mod, lambda_context):
		# A cache hit must short-circuit the DynamoDB read entirely.
		job = {'job_id': 'job-1', 'user_id': 'user-1', 'name': 'cached'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'cache_get', return_value=job), \
			 patch.object(handler_mod, 'get_job') as mock_get, \
			 patch.object(handler_mod, 'cache_set') as mock_set:
			resp = handler_mod.get_job_details_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 200
		assert json.loads(resp['body'])['name'] == 'cached'
		mock_get.assert_not_called()
		mock_set.assert_not_called()

	def test_cache_miss_reads_db_and_populates_cache(self, handler_mod, lambda_context):
		# On a miss the handler reads get_job then writes it back with a 60s TTL.
		job = {'job_id': 'job-1', 'user_id': 'user-1', 'name': 'fresh'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'cache_get', return_value=None), \
			 patch.object(handler_mod, 'get_job', return_value=job) as mock_get, \
			 patch.object(handler_mod, 'cache_set') as mock_set:
			resp = handler_mod.get_job_details_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 200
		mock_get.assert_called_once_with('job-1')
		# Cached under the namespaced key, with the job value + ttl 60. (get_job
		# already decimal-normalizes its result and the handler re-wraps it in
		# decimal_to_float before caching; with no Decimals in this fixture the
		# cached value equals the job dict, so this pins the key/ttl/value of the
		# write, not the Decimal->float conversion itself.)
		assert mock_set.call_args.args[0] == 'job:job-1'
		assert mock_set.call_args.args[1] == job
		assert mock_set.call_args.kwargs['ttl'] == 60

	def test_not_found_returns_404(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'cache_get', return_value=None), \
			 patch.object(handler_mod, 'get_job', return_value=None):
			resp = handler_mod.get_job_details_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 404
		assert json.loads(resp['body'])['message'] == 'Job not found'

	def test_foreign_owner_returns_403(self, handler_mod, lambda_context):
		# REAL verify_resource_ownership: a job owned by user-2 is forbidden to
		# user-1. This is the leak guard, exercised end-to-end (not mocked).
		job = {'job_id': 'job-1', 'user_id': 'user-2'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'cache_get', return_value=job):
			resp = handler_mod.get_job_details_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 403
		assert 'permission' in json.loads(resp['body'])['message'].lower()

	def test_owner_gets_200_with_credentialed_headers(self, handler_mod, lambda_context):
		job = {'job_id': 'job-1', 'user_id': 'user-1', 'name': 'mine'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'cache_get', return_value=job):
			resp = handler_mod.get_job_details_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 200
		assert json.loads(resp['body'])['name'] == 'mine'
		assert resp['headers']['Access-Control-Allow-Credentials'] is True


# ---------------------------------------------------------------------------
# get_crawl_handler — one crawl under a job (ownership of the PARENT job)
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestGetCrawlHandler:
	def _path(self, job_id='job-1', crawl_id='crawl-1'):
		return _event(path_params={'job_id': job_id, 'crawl_id': crawl_id})

	def test_missing_token_returns_401(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value=None):
			resp = handler_mod.get_crawl_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 401

	def test_parent_job_not_found_returns_404(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=None):
			resp = handler_mod.get_crawl_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 404
		assert json.loads(resp['body'])['message'] == 'Job not found'

	def test_foreign_parent_job_returns_403(self, handler_mod, lambda_context):
		# Ownership is checked on the PARENT job before any crawl is read.
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-2'}), \
			 patch.object(handler_mod, 'get_crawl') as mock_crawl:
			resp = handler_mod.get_crawl_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 403
		# The crawl is never read once ownership fails.
		mock_crawl.assert_not_called()

	def test_crawl_found_returns_200(self, handler_mod, lambda_context):
		crawl = {'crawl_id': 'crawl-1', 'status': 'completed'}
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}), \
			 patch.object(handler_mod, 'get_crawl', return_value=crawl) as mock_crawl:
			resp = handler_mod.get_crawl_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 200
		assert json.loads(resp['body'])['crawl_id'] == 'crawl-1'
		mock_crawl.assert_called_once_with('job-1', 'crawl-1')

	def test_crawl_not_found_returns_404(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}), \
			 patch.object(handler_mod, 'get_crawl', return_value=None):
			resp = handler_mod.get_crawl_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 404
		assert json.loads(resp['body'])['message'] == 'Crawl not found'


# ---------------------------------------------------------------------------
# get_job_crawls_handler — all crawls under a job
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestGetJobCrawlsHandler:
	def _path(self, job_id='job-1'):
		return _event(path_params={'job_id': job_id})

	def test_missing_token_returns_401(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value=None):
			resp = handler_mod.get_job_crawls_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 401

	def test_parent_job_not_found_returns_404(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=None):
			resp = handler_mod.get_job_crawls_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 404

	def test_foreign_parent_job_returns_403(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-2'}), \
			 patch.object(handler_mod, 'get_job_crawls') as mock_crawls:
			resp = handler_mod.get_job_crawls_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 403
		mock_crawls.assert_not_called()

	def test_owner_gets_200_with_crawls(self, handler_mod, lambda_context):
		crawls = [{'crawl_id': 'c1'}, {'crawl_id': 'c2'}]
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}), \
			 patch.object(handler_mod, 'get_job_crawls', return_value=crawls):
			resp = handler_mod.get_job_crawls_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		assert [c['crawl_id'] for c in body] == ['c1', 'c2']
		assert resp['headers']['Access-Control-Allow-Credentials'] is True

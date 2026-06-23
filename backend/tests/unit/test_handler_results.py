"""Unit tests for handler.py result-retrieval surface (issue #40, group 4).

Groups 1-3 pinned create_job, the read surface (list/detail/crawls), and the
lifecycle transitions. This file covers the LAST handler group: the two endpoints
a client hits to get its scraped data back out of a finished job:

  - download_results_handler   (pre-signed S3 URL, JSON/CSV/XLSX/SQL, on-demand convert)
  - preview_results_handler    (paginated in-line preview of the JSON results)

These are CHARACTERIZATION tests (no source change): they pin the CURRENT behavior so
a future regression fails loudly. Both endpoints share the load-bearing SECURITY
preamble every other handler has -- a read must require a token, 404 a missing job,
and only ever serve a job the caller OWNS -- and the 403 tests do NOT mock
`verify_resource_ownership`: they hand the handler a job whose `user_id` differs from
the resolved caller so the REAL `utils.verify_resource_ownership` (raises
PermissionError -> 403) is genuinely exercised, not stubbed into a tautology.

Beyond the preamble each endpoint has its own contract this file pins:
  - download: the `valid_formats` allow-list (parquet/xml -> clean 400, NOT a 500),
    the "no result.json -> 404" gate, the JSON-uses-original vs other-formats-convert
    branch, the cached-converted-file short-circuit (FormatConverter NOT called), the
    per-format converter dispatch (csv/xlsx/sql + the sql_table_name + flatten args),
    the conversion-failure -> 500, and the 1h pre-signed URL + file_size response shape.
  - preview: the page/page_size clamps (page<1 -> 1; page_size out of 1..100 -> 50),
    the slice math, total_pages / has_next / has_previous, columns-from-first-row,
    the missing-`results`-key -> [] default, and the malformed-page-param -> 500.

handler.py binds its S3 client (`s3 = get_s3_client()`) and the CORS allow-set at
import, so it is reloaded fresh inside a moto context per test (the `handler_mod`
fixture). S3 is REAL moto here: tests seed `jobs/<id>/result.json` through the same
mocked client the handler holds, so head_object/get_object/generate_presigned_url run
for real. The auth + data-access helpers are `from ... import`ed into handler's
namespace, so they are patched as attributes of the reloaded module; FormatConverter
is a call-time `from format_converter import FormatConverter`, so it is patched on the
`format_converter` module (the reference the source resolves at call time).
"""
import importlib
import json
from contextlib import ExitStack
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws

BUCKET = 'snowscrape-results-test'


@pytest.fixture
def handler_mod(aws_credentials, mock_env_vars):
	"""Import handler.py fresh inside a moto context, with the results bucket created."""
	with mock_aws():
		import handler as handler_module
		importlib.reload(handler_module)
		# The handler's own s3 client is moto-backed; create the bucket it reads.
		handler_module.s3.create_bucket(
			Bucket=BUCKET,
			CreateBucketConfiguration={'LocationConstraint': 'us-east-2'},
		)
		yield handler_module


def _event(path_params=None, query_params=None, origin=None):
	"""Build a minimal API Gateway proxy event."""
	event = {'headers': {}}
	if origin is not None:
		event['headers']['origin'] = origin
	if path_params is not None:
		event['pathParameters'] = path_params
	if query_params is not None:
		event['queryStringParameters'] = query_params
	return event


def _put_json(handler_mod, key, payload):
	"""Seed an S3 object through the handler's own (moto) client."""
	handler_mod.s3.put_object(
		Bucket=BUCKET, Key=key, Body=json.dumps(payload).encode('utf-8'))


def _put_raw(handler_mod, key, body=b'converted-bytes'):
	handler_mod.s3.put_object(Bucket=BUCKET, Key=key, Body=body)


# ===========================================================================
# download_results_handler
# ===========================================================================
@pytest.mark.unit
class TestDownloadResultsAuth:
	def _path(self, job_id='job-1'):
		return _event(path_params={'job_id': job_id})

	def test_missing_token_returns_401(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value=None):
			resp = handler_mod.download_results_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'Unauthorized - No token provided'
		assert 'Access-Control-Allow-Origin' in resp['headers']

	def test_invalid_token_returns_401_with_message(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', side_effect=Exception('bad token')):
			resp = handler_mod.download_results_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'bad token'

	def test_job_not_found_returns_404(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=None):
			resp = handler_mod.download_results_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 404
		assert json.loads(resp['body'])['message'] == 'Job not found'

	def test_foreign_owner_returns_403(self, handler_mod, lambda_context):
		# REAL verify_resource_ownership: a job owned by user-2 is forbidden to user-1.
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-2'}):
			resp = handler_mod.download_results_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 403
		assert 'permission' in json.loads(resp['body'])['message'].lower()


@pytest.mark.unit
class TestDownloadResultsFormatValidation:
	def _owned(self, handler_mod):
		return [
			patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
			patch.object(handler_mod, 'resolve_user_id', return_value='user-1'),
			patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}),
		]

	@pytest.mark.parametrize('bad_format', ['parquet', 'xml', 'txt', 'pdf'])
	def test_invalid_format_returns_clean_400(self, handler_mod, lambda_context, bad_format):
		# parquet (needs pyarrow, not bundled) and any other unknown format are
		# rejected with a 400 BEFORE any S3 read -- not allowed to reach a 500.
		ev = _event(path_params={'job_id': 'job-1'}, query_params={'format': bad_format})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			resp = handler_mod.download_results_handler(ev, lambda_context)
		assert resp['statusCode'] == 400
		assert resp['body'] and 'Invalid format' in json.loads(resp['body'])['message']
		assert 'json, csv, xlsx, sql' in json.loads(resp['body'])['message']

	def test_results_file_missing_returns_404(self, handler_mod, lambda_context):
		# Job exists + owned, but no jobs/<id>/result.json in S3.
		ev = _event(path_params={'job_id': 'job-1'})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			resp = handler_mod.download_results_handler(ev, lambda_context)
		assert resp['statusCode'] == 404
		assert json.loads(resp['body'])['message'] == 'Results not found for this job'


@pytest.mark.unit
class TestDownloadResultsJson:
	def _owned(self, handler_mod):
		return [
			patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
			patch.object(handler_mod, 'resolve_user_id', return_value='user-1'),
			patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}),
		]

	def test_json_uses_original_file_and_returns_presigned_url(self, handler_mod, lambda_context):
		# JSON is the native format: the original result.json is served directly, no
		# conversion, and a 1h pre-signed URL + the file size is returned.
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': [{'a': 1}]})
		ev = _event(path_params={'job_id': 'job-1'})  # no format -> defaults to json
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			# FormatConverter must never be touched on the JSON path.
			with patch('format_converter.FormatConverter') as mock_fc:
				resp = handler_mod.download_results_handler(ev, lambda_context)
				mock_fc.assert_not_called()
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		assert body['format'] == 'json'
		assert body['expires_in'] == 3600
		assert body['download_url']  # a non-empty pre-signed URL string
		# The presigned URL points at the ORIGINAL result.json, not a converted key.
		assert 'jobs/job-1/result.json' in body['download_url']
		assert body['file_size_bytes'] > 0

	def test_format_is_case_insensitive(self, handler_mod, lambda_context):
		# 'JSON' is lower-cased before the allow-list check, so it is valid.
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': []})
		ev = _event(path_params={'job_id': 'job-1'}, query_params={'format': 'JSON'})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			resp = handler_mod.download_results_handler(ev, lambda_context)
		assert resp['statusCode'] == 200
		assert json.loads(resp['body'])['format'] == 'json'


@pytest.mark.unit
class TestDownloadResultsConversion:
	def _owned(self, handler_mod):
		return [
			patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
			patch.object(handler_mod, 'resolve_user_id', return_value='user-1'),
			patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}),
		]

	def test_cached_converted_file_short_circuits_conversion(self, handler_mod, lambda_context):
		# When jobs/<id>/result.csv already exists, the handler reuses it and never
		# constructs a FormatConverter.
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': [{'a': 1}]})
		_put_raw(handler_mod, 'jobs/job-1/result.csv', b'a\n1\n')
		ev = _event(path_params={'job_id': 'job-1'}, query_params={'format': 'csv'})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			with patch('format_converter.FormatConverter') as mock_fc:
				resp = handler_mod.download_results_handler(ev, lambda_context)
				mock_fc.assert_not_called()
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		assert body['format'] == 'csv'
		assert 'jobs/job-1/result.csv' in body['download_url']

	def test_csv_conversion_invoked_when_converted_file_absent(self, handler_mod, lambda_context):
		# No result.csv yet: the converter is built with (job_id, the loaded JSON
		# results, bucket), prepare_dataframe(flatten=...) runs, then convert_to_csv
		# is called with the target key.
		results_payload = {'results': [{'a': 1}, {'a': 2}]}
		_put_json(handler_mod, 'jobs/job-1/result.json', results_payload)
		ev = _event(path_params={'job_id': 'job-1'}, query_params={'format': 'csv'})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			with patch('format_converter.FormatConverter') as mock_fc:
				instance = mock_fc.return_value
				resp = handler_mod.download_results_handler(ev, lambda_context)
		assert resp['statusCode'] == 200
		# Constructor: (job_id, results_data, bucket)
		mock_fc.assert_called_once()
		args = mock_fc.call_args.args
		assert args[0] == 'job-1'
		assert args[1] == results_payload
		assert args[2] == BUCKET
		instance.prepare_dataframe.assert_called_once_with(flatten=False)
		instance.convert_to_csv.assert_called_once_with('jobs/job-1/result.csv')
		# The converter wrote no real file, so the size head_object fails and falls
		# back to 0 -- the request still succeeds.
		assert json.loads(resp['body'])['file_size_bytes'] == 0

	def test_flatten_query_param_forwarded_to_prepare_dataframe(self, handler_mod, lambda_context):
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': [{'a': 1}]})
		ev = _event(path_params={'job_id': 'job-1'},
					query_params={'format': 'csv', 'flatten': 'true'})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			with patch('format_converter.FormatConverter') as mock_fc:
				handler_mod.download_results_handler(ev, lambda_context)
		mock_fc.return_value.prepare_dataframe.assert_called_once_with(flatten=True)

	def test_xlsx_dispatches_convert_to_xlsx(self, handler_mod, lambda_context):
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': [{'a': 1}]})
		ev = _event(path_params={'job_id': 'job-1'}, query_params={'format': 'xlsx'})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			with patch('format_converter.FormatConverter') as mock_fc:
				resp = handler_mod.download_results_handler(ev, lambda_context)
		assert resp['statusCode'] == 200
		mock_fc.return_value.convert_to_xlsx.assert_called_once_with('jobs/job-1/result.xlsx')
		mock_fc.return_value.convert_to_csv.assert_not_called()

	def test_sql_dispatches_with_default_table_name(self, handler_mod, lambda_context):
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': [{'a': 1}]})
		ev = _event(path_params={'job_id': 'job-1'}, query_params={'format': 'sql'})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			with patch('format_converter.FormatConverter') as mock_fc:
				handler_mod.download_results_handler(ev, lambda_context)
		mock_fc.return_value.convert_to_sql.assert_called_once_with(
			'jobs/job-1/result.sql', 'scraped_data')

	def test_sql_honors_custom_table_name(self, handler_mod, lambda_context):
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': [{'a': 1}]})
		ev = _event(path_params={'job_id': 'job-1'},
					query_params={'format': 'sql', 'sql_table_name': 'my_table'})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			with patch('format_converter.FormatConverter') as mock_fc:
				handler_mod.download_results_handler(ev, lambda_context)
		mock_fc.return_value.convert_to_sql.assert_called_once_with(
			'jobs/job-1/result.sql', 'my_table')

	def test_conversion_failure_returns_500(self, handler_mod, lambda_context):
		# A converter import/prepare/convert error is caught and surfaced as a clean
		# 500 naming the format (issue #32), not an unhandled exception.
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': [{'a': 1}]})
		ev = _event(path_params={'job_id': 'job-1'}, query_params={'format': 'csv'})
		with ExitStack() as es:
			for p in self._owned(handler_mod):
				es.enter_context(p)
			with patch('format_converter.FormatConverter') as mock_fc:
				mock_fc.return_value.convert_to_csv.side_effect = RuntimeError('boom')
				resp = handler_mod.download_results_handler(ev, lambda_context)
		assert resp['statusCode'] == 500
		assert 'Failed to convert to csv' in json.loads(resp['body'])['message']
		assert 'boom' in json.loads(resp['body'])['message']


@pytest.mark.unit
class TestDownloadResultsTopLevelError:
	def test_missing_path_parameters_returns_500(self, handler_mod, lambda_context):
		# event without pathParameters -> KeyError -> the outer except -> 500 with the
		# generic download-failure envelope (not a leak of the raw traceback as 200).
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'):
			resp = handler_mod.download_results_handler(_event(), lambda_context)
		assert resp['statusCode'] == 500
		assert json.loads(resp['body'])['message'] == 'Failed to generate download URL'


# ===========================================================================
# preview_results_handler
# ===========================================================================
@pytest.mark.unit
class TestPreviewResultsAuth:
	def _path(self, job_id='job-1'):
		return _event(path_params={'job_id': job_id})

	def test_missing_token_returns_401(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value=None):
			resp = handler_mod.preview_results_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'Unauthorized - No token provided'

	def test_invalid_token_returns_401_with_message(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', side_effect=Exception('nope')):
			resp = handler_mod.preview_results_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 401
		assert json.loads(resp['body'])['message'] == 'nope'

	def test_job_not_found_returns_404(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value=None):
			resp = handler_mod.preview_results_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 404
		assert json.loads(resp['body'])['message'] == 'Job not found'

	def test_foreign_owner_returns_403(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-2'}):
			resp = handler_mod.preview_results_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 403
		assert 'permission' in json.loads(resp['body'])['message'].lower()

	def test_results_file_missing_returns_404(self, handler_mod, lambda_context):
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}):
			resp = handler_mod.preview_results_handler(self._path(), lambda_context)
		assert resp['statusCode'] == 404
		assert json.loads(resp['body'])['message'] == 'Results not found for this job'


@pytest.mark.unit
class TestPreviewResultsPagination:
	"""All of these need an owned job + a seeded result.json."""

	def _setup(self, handler_mod, rows):
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': rows})
		return [
			patch.object(handler_mod, 'extract_token_from_event', return_value='tok'),
			patch.object(handler_mod, 'resolve_user_id', return_value='user-1'),
			patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}),
		]

	def _run(self, handler_mod, lambda_context, rows, query_params=None):
		patchers = self._setup(handler_mod, rows)
		ev = _event(path_params={'job_id': 'job-1'}, query_params=query_params)
		with ExitStack() as es:
			for p in patchers:
				es.enter_context(p)
			return handler_mod.preview_results_handler(ev, lambda_context)

	def test_default_page_and_page_size(self, handler_mod, lambda_context):
		rows = [{'col': i} for i in range(120)]
		resp = self._run(handler_mod, lambda_context, rows)
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		# Default: page 1, page_size 50 -> first 50 rows.
		assert len(body['results']) == 50
		assert body['results'][0] == {'col': 0}
		pg = body['pagination']
		assert pg['page'] == 1
		assert pg['page_size'] == 50
		assert pg['total_count'] == 120
		assert pg['total_pages'] == 3  # ceil(120/50)
		assert pg['has_next'] is True
		assert pg['has_previous'] is False

	def test_second_page_slice_and_flags(self, handler_mod, lambda_context):
		rows = [{'col': i} for i in range(120)]
		resp = self._run(handler_mod, lambda_context, rows,
						 query_params={'page': '2', 'page_size': '50'})
		body = json.loads(resp['body'])
		assert body['results'][0] == {'col': 50}
		assert len(body['results']) == 50
		assert body['pagination']['has_next'] is True
		assert body['pagination']['has_previous'] is True

	def test_last_page_partial_slice(self, handler_mod, lambda_context):
		rows = [{'col': i} for i in range(120)]
		resp = self._run(handler_mod, lambda_context, rows,
						 query_params={'page': '3', 'page_size': '50'})
		body = json.loads(resp['body'])
		# rows 100..119 -> 20 items, no next page.
		assert len(body['results']) == 20
		assert body['results'][0] == {'col': 100}
		assert body['pagination']['has_next'] is False
		assert body['pagination']['has_previous'] is True

	def test_page_below_one_is_clamped_to_one(self, handler_mod, lambda_context):
		rows = [{'col': i} for i in range(10)]
		resp = self._run(handler_mod, lambda_context, rows,
						 query_params={'page': '0', 'page_size': '5'})
		body = json.loads(resp['body'])
		assert body['pagination']['page'] == 1
		assert body['results'][0] == {'col': 0}

	@pytest.mark.parametrize('bad_size', ['0', '101', '500'])
	def test_page_size_out_of_range_falls_back_to_50(self, handler_mod, lambda_context, bad_size):
		rows = [{'col': i} for i in range(60)]
		resp = self._run(handler_mod, lambda_context, rows,
						 query_params={'page_size': bad_size})
		body = json.loads(resp['body'])
		assert body['pagination']['page_size'] == 50
		assert len(body['results']) == 50

	def test_columns_taken_from_first_row(self, handler_mod, lambda_context):
		rows = [{'name': 'a', 'price': 1}, {'name': 'b', 'price': 2}]
		resp = self._run(handler_mod, lambda_context, rows)
		body = json.loads(resp['body'])
		assert body['columns'] == ['name', 'price']

	def test_empty_results_list(self, handler_mod, lambda_context):
		resp = self._run(handler_mod, lambda_context, [])
		body = json.loads(resp['body'])
		assert body['results'] == []
		assert body['columns'] == []
		assert body['pagination']['total_count'] == 0
		assert body['pagination']['total_pages'] == 0
		assert body['pagination']['has_next'] is False
		assert body['pagination']['has_previous'] is False


@pytest.mark.unit
class TestPreviewResultsResultsKeyDefault:
	def test_missing_results_key_defaults_to_empty(self, handler_mod, lambda_context):
		# A result.json payload WITHOUT a 'results' key is treated as zero results
		# via .get('results', []), not a 500.
		_put_json(handler_mod, 'jobs/job-1/result.json', {'metadata': {'foo': 'bar'}})
		ev = _event(path_params={'job_id': 'job-1'})
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}):
			resp = handler_mod.preview_results_handler(ev, lambda_context)
		assert resp['statusCode'] == 200
		body = json.loads(resp['body'])
		assert body['results'] == []
		assert body['pagination']['total_count'] == 0


@pytest.mark.unit
class TestPreviewResultsTopLevelError:
	def test_non_integer_page_param_returns_500(self, handler_mod, lambda_context):
		# int('abc') raises ValueError AFTER the ownership check + S3 read, so it is
		# caught by the outer except -> 500 generic envelope.
		_put_json(handler_mod, 'jobs/job-1/result.json', {'results': [{'a': 1}]})
		ev = _event(path_params={'job_id': 'job-1'}, query_params={'page': 'abc'})
		with patch.object(handler_mod, 'extract_token_from_event', return_value='tok'), \
			 patch.object(handler_mod, 'resolve_user_id', return_value='user-1'), \
			 patch.object(handler_mod, 'get_job', return_value={'job_id': 'job-1', 'user_id': 'user-1'}):
			resp = handler_mod.preview_results_handler(ev, lambda_context)
		assert resp['statusCode'] == 500
		assert json.loads(resp['body'])['message'] == 'Failed to fetch results preview'

"""Characterization tests for logger.py.

`logger.py` is the most widely imported backend module: every Lambda handler and
helper does `logger = get_logger(__name__)` and emits structured JSON that
CloudWatch parses. It had ZERO dedicated coverage, yet it is a contract boundary
in two directions:

- The emitted log line is the JSON string produced by `_build_log_entry` ->
  `json.dumps`. Its shape (timestamp / level / message / merged context / extra /
  error block) is consumed by CloudWatch Insights queries and any dashboard that
  filters on those fields. A regression that drops `timestamp`, renames `level`,
  or changes the field-merge order silently breaks log search.
- The level gate, the singleton cache, and the from-`sys.exc_info` traceback are
  load-bearing behaviors with non-obvious edges a smoke test never exercises.

These tests pin the current behavior with NO source change. Output is captured by
attaching a recording `logging.Handler` to the StructuredLogger's underlying
stdlib logger (and turning off propagation) so the exact emitted record is read
back and the JSON parsed, rather than relying on stdout (the module's own
StreamHandler binds `sys.stdout` at construction, which pytest capture cannot
intercept). Each test uses a unique logger name to avoid stdlib logger global
state bleeding across tests.
"""
import json
import logging
import sys

import pytest

import logger as logger_module
from logger import (
	StructuredLogger,
	JsonFormatter,
	get_logger,
	log_lambda_invocation,
	log_exception,
)


class RecordingHandler(logging.Handler):
	"""Captures emitted LogRecords so the exact JSON line can be read back."""

	def __init__(self):
		super().__init__()
		self.records = []

	def emit(self, record):
		self.records.append(record)

	def messages(self):
		return [r.getMessage() for r in self.records]

	def entries(self):
		return [json.loads(r.getMessage()) for r in self.records]


def attach_recorder(sl):
	"""Attach a recorder to a StructuredLogger and isolate it from propagation."""
	rec = RecordingHandler()
	sl.logger.addHandler(rec)
	# Stop records bubbling to the root logger so pytest's own log capture and
	# the recorder don't double-handle / interfere.
	sl.logger.propagate = False
	return rec


class TestStructuredLoggerInit:
	"""The constructor's handler/level/context contract."""

	def test_sets_requested_level(self):
		sl = StructuredLogger('test_init.level', level=logging.WARNING)
		assert sl.logger.level == logging.WARNING

	def test_defaults_to_info_level(self):
		sl = StructuredLogger('test_init.default')
		assert sl.logger.level == logging.INFO

	def test_installs_exactly_one_handler(self):
		sl = StructuredLogger('test_init.one_handler')
		assert len(sl.logger.handlers) == 1

	def test_handler_is_streamhandler_to_stdout(self):
		sl = StructuredLogger('test_init.stdout')
		handler = sl.logger.handlers[0]
		assert isinstance(handler, logging.StreamHandler)
		# CloudWatch reads the function's stdout; this is the delivery contract.
		assert handler.stream is sys.stdout

	def test_handler_uses_json_formatter(self):
		sl = StructuredLogger('test_init.formatter')
		assert isinstance(sl.logger.handlers[0].formatter, JsonFormatter)

	def test_context_starts_empty(self):
		sl = StructuredLogger('test_init.context')
		assert sl.context == {}

	def test_reinit_same_name_does_not_accumulate_handlers(self):
		# Re-creating a logger for the same name must reset handlers to exactly
		# one, otherwise each construction would add another stdout handler and
		# every line would be emitted N times (duplicate-log regression).
		name = 'test_init.no_dupe'
		StructuredLogger(name)
		StructuredLogger(name)
		sl = StructuredLogger(name)
		assert len(sl.logger.handlers) == 1


class TestContext:
	"""set_context / clear_context accumulation and propagation into entries."""

	def test_set_context_adds_values(self):
		sl = StructuredLogger('test_ctx.add')
		sl.set_context(user_id='u1')
		assert sl.context == {'user_id': 'u1'}

	def test_set_context_accumulates(self):
		sl = StructuredLogger('test_ctx.accumulate')
		sl.set_context(user_id='u1')
		sl.set_context(job_id='j1')
		assert sl.context == {'user_id': 'u1', 'job_id': 'j1'}

	def test_set_context_overwrites_same_key(self):
		sl = StructuredLogger('test_ctx.overwrite')
		sl.set_context(user_id='u1')
		sl.set_context(user_id='u2')
		assert sl.context == {'user_id': 'u2'}

	def test_clear_context_empties(self):
		sl = StructuredLogger('test_ctx.clear')
		sl.set_context(user_id='u1', job_id='j1')
		sl.clear_context()
		assert sl.context == {}

	def test_context_appears_in_every_entry(self):
		sl = StructuredLogger('test_ctx.in_entry')
		rec = attach_recorder(sl)
		sl.set_context(request_id='r1')
		sl.info('first')
		sl.info('second')
		entries = rec.entries()
		assert all(e['request_id'] == 'r1' for e in entries)


class TestEntryShape:
	"""The base JSON shape and field-merge precedence."""

	def test_base_fields_present(self):
		sl = StructuredLogger('test_shape.base')
		rec = attach_recorder(sl)
		sl.info('hello')
		entry = rec.entries()[0]
		assert entry['level'] == 'INFO'
		assert entry['message'] == 'hello'
		assert 'timestamp' in entry

	def test_timestamp_is_iso_utc(self):
		from datetime import datetime
		sl = StructuredLogger('test_shape.timestamp')
		rec = attach_recorder(sl)
		sl.info('hello')
		ts = rec.entries()[0]['timestamp']
		# isoformat() of a tz-aware UTC datetime ends with the +00:00 offset and
		# round-trips through fromisoformat.
		assert ts.endswith('+00:00')
		parsed = datetime.fromisoformat(ts)
		assert parsed.utcoffset().total_seconds() == 0

	def test_kwargs_become_top_level_fields(self):
		sl = StructuredLogger('test_shape.kwargs')
		rec = attach_recorder(sl)
		sl.info('hello', job_id='j1', count=3)
		entry = rec.entries()[0]
		assert entry['job_id'] == 'j1'
		assert entry['count'] == 3

	def test_nested_dict_kwarg_preserved(self):
		sl = StructuredLogger('test_shape.nested')
		rec = attach_recorder(sl)
		sl.info('hello', data={'a': 1, 'b': [2, 3]})
		assert rec.entries()[0]['data'] == {'a': 1, 'b': [2, 3]}

	def test_kwargs_override_context_on_collision(self):
		# _build_log_entry merges context first, then extra (kwargs), so a kwarg
		# wins over a same-named context value.
		sl = StructuredLogger('test_shape.kw_over_ctx')
		rec = attach_recorder(sl)
		sl.set_context(source='ctx')
		sl.info('hello', source='kw')
		assert rec.entries()[0]['source'] == 'kw'

	def test_context_can_shadow_base_field(self):
		# Characterization of the merge ORDER: base fields are written first, then
		# **context, so a context key colliding with a base field name (here
		# 'level') overrides the base value. Unusual, but it is the real behavior;
		# a regression that reordered the merge would change it.
		sl = StructuredLogger('test_shape.ctx_shadow')
		rec = attach_recorder(sl)
		sl.set_context(level='SHADOWED')
		sl.info('hello')
		assert rec.entries()[0]['level'] == 'SHADOWED'

	def test_no_error_key_without_error(self):
		sl = StructuredLogger('test_shape.no_error')
		rec = attach_recorder(sl)
		sl.info('hello')
		assert 'error' not in rec.entries()[0]

	def test_non_json_serializable_kwarg_raises(self):
		# Unlike cache.py's cache_set (which passes default=str), the logger calls
		# json.dumps with no default, so a non-JSON-native value raises TypeError.
		from datetime import datetime, timezone
		sl = StructuredLogger('test_shape.nonjson')
		attach_recorder(sl)
		with pytest.raises(TypeError):
			sl.info('hello', when=datetime.now(timezone.utc))


class TestLevelMethods:
	"""Each level method emits at the matching severity, honoring the gate."""

	@pytest.mark.parametrize('method,level_str,levelno', [
		('info', 'INFO', logging.INFO),
		('warning', 'WARNING', logging.WARNING),
		('error', 'ERROR', logging.ERROR),
		('critical', 'CRITICAL', logging.CRITICAL),
	])
	def test_level_field_and_record_severity(self, method, level_str, levelno):
		sl = StructuredLogger(f'test_level.{method}', level=logging.DEBUG)
		rec = attach_recorder(sl)
		getattr(sl, method)('msg')
		record = rec.records[0]
		assert rec.entries()[0]['level'] == level_str
		assert record.levelno == levelno

	def test_debug_emits_when_level_is_debug(self):
		sl = StructuredLogger('test_level.debug_on', level=logging.DEBUG)
		rec = attach_recorder(sl)
		sl.debug('msg')
		assert rec.entries()[0]['level'] == 'DEBUG'

	def test_debug_filtered_at_default_info_level(self):
		# The logger-level gate (isEnabledFor) drops DEBUG before any handler, so
		# nothing is recorded at the default INFO level.
		sl = StructuredLogger('test_level.debug_off')
		rec = attach_recorder(sl)
		sl.debug('msg')
		assert rec.records == []

	def test_info_filtered_when_level_is_warning(self):
		sl = StructuredLogger('test_level.info_off', level=logging.WARNING)
		rec = attach_recorder(sl)
		sl.info('msg')
		assert rec.records == []
		sl.warning('msg')
		assert len(rec.records) == 1


class TestErrorTraceback:
	"""The error/critical exception block, including the sys.exc_info quirk."""

	def test_error_block_type_and_message(self):
		sl = StructuredLogger('test_err.fields')
		rec = attach_recorder(sl)
		try:
			raise ValueError('boom')
		except ValueError as e:
			sl.error('it failed', error=e)
		err = rec.entries()[0]['error']
		assert err['type'] == 'ValueError'
		assert err['message'] == 'boom'

	def test_error_traceback_from_active_exception(self):
		sl = StructuredLogger('test_err.tb_active')
		rec = attach_recorder(sl)
		try:
			raise ValueError('boom')
		except ValueError as e:
			sl.error('it failed', error=e)
		tb = rec.entries()[0]['error']['traceback']
		assert 'Traceback' in tb
		assert 'ValueError' in tb

	def test_error_traceback_uses_exc_info_not_passed_error(self):
		# GOTCHA: the traceback comes from traceback.format_exc() (the CURRENT
		# sys.exc_info), NOT from the passed exception. Passing a constructed-but-
		# never-raised exception outside any except block yields the no-active-
		# exception sentinel, even though type/message are taken from the object.
		sl = StructuredLogger('test_err.tb_detached')
		rec = attach_recorder(sl)
		sl.error('it failed', error=ValueError('boom'))
		err = rec.entries()[0]['error']
		assert err['type'] == 'ValueError'
		assert err['message'] == 'boom'
		assert err['traceback'] == 'NoneType: None\n'

	def test_critical_includes_error_block(self):
		sl = StructuredLogger('test_err.critical', level=logging.DEBUG)
		rec = attach_recorder(sl)
		try:
			raise RuntimeError('fatal')
		except RuntimeError as e:
			sl.critical('down', error=e)
		entry = rec.entries()[0]
		assert entry['level'] == 'CRITICAL'
		assert entry['error']['type'] == 'RuntimeError'

	def test_error_without_exception_has_no_error_block(self):
		sl = StructuredLogger('test_err.no_exc')
		rec = attach_recorder(sl)
		sl.error('plain error message')
		assert 'error' not in rec.entries()[0]

	def test_error_kwargs_still_included(self):
		sl = StructuredLogger('test_err.kwargs')
		rec = attach_recorder(sl)
		sl.error('it failed', error=ValueError('x'), job_id='j1')
		assert rec.entries()[0]['job_id'] == 'j1'


class TestConvenienceMethods:
	"""log_request / log_job_event / log_url_crawl field contracts."""

	def test_log_request_fields(self):
		sl = StructuredLogger('test_conv.request')
		rec = attach_recorder(sl)
		sl.log_request('GET', '/jobs', 200, 12.5, user_id='u1')
		entry = rec.entries()[0]
		assert entry['level'] == 'INFO'
		assert entry['message'] == 'HTTP Request'
		assert entry['http_method'] == 'GET'
		assert entry['http_path'] == '/jobs'
		assert entry['http_status_code'] == 200
		assert entry['duration_ms'] == 12.5
		assert entry['user_id'] == 'u1'

	def test_log_job_event_fields(self):
		sl = StructuredLogger('test_conv.job_event')
		rec = attach_recorder(sl)
		sl.log_job_event('j1', 'completed', 'ready')
		entry = rec.entries()[0]
		# The event name is interpolated into the message AND echoed as a field.
		assert entry['message'] == 'Job completed'
		assert entry['job_id'] == 'j1'
		assert entry['job_event'] == 'completed'
		assert entry['job_status'] == 'ready'

	def test_log_url_crawl_fields(self):
		sl = StructuredLogger('test_conv.url_crawl')
		rec = attach_recorder(sl)
		sl.log_url_crawl('j1', 'https://example.com', 'success', 42.0, tier=1)
		entry = rec.entries()[0]
		assert entry['message'] == 'URL crawl attempt'
		assert entry['job_id'] == 'j1'
		assert entry['url'] == 'https://example.com'
		assert entry['crawl_status'] == 'success'
		assert entry['duration_ms'] == 42.0
		assert entry['tier'] == 1


class TestJsonFormatter:
	"""The formatter is a pass-through of the already-rendered message."""

	def test_returns_message_verbatim(self):
		rec = logging.LogRecord('n', logging.INFO, __file__, 1, '{"a": 1}', None, None)
		assert JsonFormatter().format(rec) == '{"a": 1}'

	def test_applies_record_args(self):
		# getMessage() performs %-style arg substitution; StructuredLogger never
		# passes args, but the formatter's contract is whatever getMessage yields.
		rec = logging.LogRecord('n', logging.INFO, __file__, 1, 'val=%s', ('x',), None)
		assert JsonFormatter().format(rec) == 'val=x'


class TestGetLogger:
	"""The module-level singleton cache."""

	def setup_method(self):
		logger_module._loggers.clear()

	def test_returns_structured_logger(self):
		assert isinstance(get_logger('test_get.a'), StructuredLogger)

	def test_same_name_returns_same_instance(self):
		assert get_logger('test_get.same') is get_logger('test_get.same')

	def test_different_names_distinct_instances(self):
		assert get_logger('test_get.x') is not get_logger('test_get.y')

	def test_cached_instance_ignores_later_level_arg(self):
		# The cache returns the first instance; a later call's level is ignored.
		first = get_logger('test_get.level', level=logging.DEBUG)
		second = get_logger('test_get.level', level=logging.ERROR)
		assert second is first
		assert first.logger.level == logging.DEBUG


class TestLogLambdaInvocation:
	"""log_lambda_invocation populates context from the Lambda context object."""

	def test_sets_context_from_context_object(self, lambda_context):
		sl = StructuredLogger('test_lambda.context')
		attach_recorder(sl)
		log_lambda_invocation({}, lambda_context, sl)
		assert sl.context == {
			'request_id': 'test-request-id',
			'function_name': 'test-function',
			'function_version': '1',
			'memory_limit_mb': 128,
		}

	def test_emits_invocation_entry(self, lambda_context):
		sl = StructuredLogger('test_lambda.entry')
		rec = attach_recorder(sl)
		event = {'requestContext': {'requestType': 'CONNECT'}}
		log_lambda_invocation(event, lambda_context, sl)
		entry = rec.entries()[0]
		assert entry['message'] == 'Lambda invocation'
		assert entry['event_type'] == 'CONNECT'
		assert entry['remaining_time_ms'] == 30000
		# Context set just before the log call is merged into the same entry.
		assert entry['request_id'] == 'test-request-id'

	def test_event_type_defaults_to_unknown(self, lambda_context):
		sl = StructuredLogger('test_lambda.unknown')
		rec = attach_recorder(sl)
		log_lambda_invocation({}, lambda_context, sl)
		assert rec.entries()[0]['event_type'] == 'unknown'


class TestLogException:
	"""log_exception is a thin delegate to logger.error with the error block."""

	def test_delegates_to_error_with_block(self):
		sl = StructuredLogger('test_logexc.block')
		rec = attach_recorder(sl)
		try:
			raise KeyError('missing')
		except KeyError as e:
			log_exception(sl, 'handler failed', e, job_id='j1')
		entry = rec.entries()[0]
		assert entry['level'] == 'ERROR'
		assert entry['message'] == 'handler failed'
		assert entry['error']['type'] == 'KeyError'
		assert entry['job_id'] == 'j1'

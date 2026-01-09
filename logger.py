import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredLogger:
	"""
	Structured logger that outputs JSON-formatted logs for CloudWatch.
	Provides context tracking and consistent log formatting.
	"""

	def __init__(self, name: str, level: int = logging.INFO):
		"""
		Initialize structured logger.

		Args:
			name: Logger name (typically module name)
			level: Logging level (default: INFO)
		"""
		self.logger = logging.getLogger(name)
		self.logger.setLevel(level)

		# Remove existing handlers to avoid duplicates
		self.logger.handlers = []

		# Configure JSON formatter for CloudWatch
		handler = logging.StreamHandler(sys.stdout)
		handler.setFormatter(JsonFormatter())
		self.logger.addHandler(handler)

		# Context dictionary for request/job tracking
		self.context = {}

	def set_context(self, **kwargs):
		"""
		Set context values that will be included in all subsequent log entries.

		Args:
			**kwargs: Key-value pairs to add to context
		"""
		self.context.update(kwargs)

	def clear_context(self):
		"""Clear all context values."""
		self.context = {}

	def _build_log_entry(
		self,
		level: str,
		message: str,
		extra: Optional[Dict[str, Any]] = None,
		error: Optional[Exception] = None
	) -> Dict[str, Any]:
		"""
		Build structured log entry.

		Args:
			level: Log level (INFO, ERROR, etc.)
			message: Log message
			extra: Additional fields to include
			error: Exception object if logging an error

		Returns:
			Dictionary containing structured log data
		"""
		log_entry = {
			'timestamp': datetime.now(timezone.utc).isoformat(),
			'level': level,
			'message': message,
			**self.context
		}

		if extra:
			log_entry.update(extra)

		if error:
			log_entry['error'] = {
				'type': type(error).__name__,
				'message': str(error),
				'traceback': traceback.format_exc()
			}

		return log_entry

	def debug(self, message: str, **kwargs):
		"""Log debug message."""
		log_entry = self._build_log_entry('DEBUG', message, kwargs)
		self.logger.debug(json.dumps(log_entry))

	def info(self, message: str, **kwargs):
		"""Log info message."""
		log_entry = self._build_log_entry('INFO', message, kwargs)
		self.logger.info(json.dumps(log_entry))

	def warning(self, message: str, **kwargs):
		"""Log warning message."""
		log_entry = self._build_log_entry('WARNING', message, kwargs)
		self.logger.warning(json.dumps(log_entry))

	def error(self, message: str, error: Optional[Exception] = None, **kwargs):
		"""
		Log error message.

		Args:
			message: Error message
			error: Exception object
			**kwargs: Additional context
		"""
		log_entry = self._build_log_entry('ERROR', message, kwargs, error)
		self.logger.error(json.dumps(log_entry))

	def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
		"""
		Log critical message.

		Args:
			message: Critical error message
			error: Exception object
			**kwargs: Additional context
		"""
		log_entry = self._build_log_entry('CRITICAL', message, kwargs, error)
		self.logger.critical(json.dumps(log_entry))

	def log_request(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs):
		"""
		Log HTTP request with timing information.

		Args:
			method: HTTP method
			path: Request path
			status_code: Response status code
			duration_ms: Request duration in milliseconds
			**kwargs: Additional request context
		"""
		self.info(
			'HTTP Request',
			http_method=method,
			http_path=path,
			http_status_code=status_code,
			duration_ms=duration_ms,
			**kwargs
		)

	def log_job_event(self, job_id: str, event: str, status: str, **kwargs):
		"""
		Log job lifecycle event.

		Args:
			job_id: Job ID
			event: Event name (created, started, completed, failed, etc.)
			status: Current job status
			**kwargs: Additional job context
		"""
		self.info(
			f'Job {event}',
			job_id=job_id,
			job_event=event,
			job_status=status,
			**kwargs
		)

	def log_url_crawl(self, job_id: str, url: str, status: str, duration_ms: float, **kwargs):
		"""
		Log URL crawl attempt.

		Args:
			job_id: Job ID
			url: URL being crawled
			status: Crawl status (success, error, timeout)
			duration_ms: Crawl duration in milliseconds
			**kwargs: Additional crawl context
		"""
		self.info(
			'URL crawl attempt',
			job_id=job_id,
			url=url,
			crawl_status=status,
			duration_ms=duration_ms,
			**kwargs
		)


class JsonFormatter(logging.Formatter):
	"""
	Custom formatter that outputs logs in JSON format.
	Used for CloudWatch structured logging.
	"""

	def format(self, record: logging.LogRecord) -> str:
		"""
		Format log record as JSON string.

		Args:
			record: Log record to format

		Returns:
			JSON-formatted log string
		"""
		# The message is already JSON from StructuredLogger
		return record.getMessage()


# Singleton logger instances
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
	"""
	Get or create a structured logger instance.

	Args:
		name: Logger name (typically module name)
		level: Logging level

	Returns:
		StructuredLogger instance
	"""
	if name not in _loggers:
		_loggers[name] = StructuredLogger(name, level)
	return _loggers[name]


def log_lambda_invocation(event: Dict[str, Any], context: Any, logger: StructuredLogger):
	"""
	Log Lambda function invocation with context.

	Args:
		event: Lambda event object
		context: Lambda context object
		logger: Logger instance
	"""
	logger.set_context(
		request_id=context.aws_request_id,
		function_name=context.function_name,
		function_version=context.function_version,
		memory_limit_mb=context.memory_limit_in_mb
	)

	logger.info(
		'Lambda invocation',
		event_type=event.get('requestContext', {}).get('requestType', 'unknown'),
		remaining_time_ms=context.get_remaining_time_in_millis()
	)


def log_exception(logger: StructuredLogger, message: str, error: Exception, **kwargs):
	"""
	Log exception with full context and traceback.

	Args:
		logger: Logger instance
		message: Error message
		error: Exception object
		**kwargs: Additional context
	"""
	logger.error(message, error=error, **kwargs)


# Example usage in Lambda handlers:
#
# from logger import get_logger, log_lambda_invocation
#
# logger = get_logger(__name__)
#
# def my_handler(event, context):
#     log_lambda_invocation(event, context, logger)
#
#     try:
#         # Handler logic
#         logger.info("Processing started", job_id="123")
#         # ...
#         logger.log_job_event("123", "completed", "ready")
#         return {"statusCode": 200}
#     except Exception as e:
#         log_exception(logger, "Handler failed", e, job_id="123")
#         return {"statusCode": 500}

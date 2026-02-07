"""
CloudWatch custom metrics for business KPIs.
Tracks job performance, crawl success rates, and operational metrics.
"""

import boto3
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from logger import get_logger

logger = get_logger(__name__)


# Use singleton pattern for CloudWatch client
_cloudwatch_client = None


def get_cloudwatch_client():
	"""Get or create CloudWatch client."""
	global _cloudwatch_client
	if _cloudwatch_client is None:
		region = os.environ.get('REGION', 'us-east-2')
		_cloudwatch_client = boto3.client('cloudwatch', region_name=region)
	return _cloudwatch_client


class MetricsEmitter:
	"""Emits custom CloudWatch metrics for business KPIs."""

	def __init__(self):
		self.cloudwatch = get_cloudwatch_client()
		self.service = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'snowscrape')
		self.stage = os.environ.get('STAGE', 'dev')
		self.namespace = f'snowscrape/{self.stage}'

	def put_metric(
		self,
		metric_name: str,
		value: float,
		unit: str = 'None',
		dimensions: Optional[List[Dict[str, str]]] = None
	):
		"""
		Put a single metric to CloudWatch.

		Args:
			metric_name: Name of the metric
			value: Metric value
			unit: Metric unit (Seconds, Count, Bytes, etc.)
			dimensions: Optional list of dimensions
		"""
		try:
			metric_data = {
				'MetricName': metric_name,
				'Value': value,
				'Unit': unit,
				'Timestamp': datetime.now(timezone.utc)
			}

			if dimensions:
				metric_data['Dimensions'] = dimensions

			self.cloudwatch.put_metric_data(
				Namespace=self.namespace,
				MetricData=[metric_data]
			)
		except Exception as e:
			# Don't fail the request if metrics fail
			logger.warning("Failed to emit metric", metric_name=metric_name, error=str(e))

	def emit_crawl_success(self, job_id: str, url: str, duration_ms: float):
		"""
		Emit metrics for successful URL crawl.

		Args:
			job_id: Job ID
			url: URL that was crawled
			duration_ms: Crawl duration in milliseconds
		"""
		dimensions = [{'Name': 'JobId', 'Value': job_id}]

		# Track crawl success
		self.put_metric('CrawlSuccess', 1, 'Count', dimensions)

		# Track crawl duration
		self.put_metric('CrawlDuration', duration_ms, 'Milliseconds', dimensions)

	def emit_crawl_failure(self, job_id: str, url: str, error_type: str):
		"""
		Emit metrics for failed URL crawl.

		Args:
			job_id: Job ID
			url: URL that failed
			error_type: Type of error (timeout, connection, parse, etc.)
		"""
		dimensions = [
			{'Name': 'JobId', 'Value': job_id},
			{'Name': 'ErrorType', 'Value': error_type}
		]

		# Track crawl failure
		self.put_metric('CrawlFailure', 1, 'Count', dimensions)

	def emit_job_processing_duration(self, job_id: str, duration_ms: float, status: str):
		"""
		Emit metrics for job processing completion.

		Args:
			job_id: Job ID
			duration_ms: Total processing duration in milliseconds
			status: Final job status (completed, cancelled, timeout, error)
		"""
		dimensions = [
			{'Name': 'JobId', 'Value': job_id},
			{'Name': 'Status', 'Value': status}
		]

		# Track job processing duration
		self.put_metric('JobProcessingDuration', duration_ms, 'Milliseconds', dimensions)

	def emit_urls_processed(self, job_id: str, count: int):
		"""
		Emit metrics for number of URLs processed in a job.

		Args:
			job_id: Job ID
			count: Number of URLs processed
		"""
		dimensions = [{'Name': 'JobId', 'Value': job_id}]

		self.put_metric('UrlsProcessed', count, 'Count', dimensions)

	def emit_job_queue_depth(self, queue_depth: int):
		"""
		Emit metric for job queue depth.

		Args:
			queue_depth: Number of jobs in queue
		"""
		self.put_metric('JobQueueDepth', queue_depth, 'Count')

	def emit_crawl_success_rate(self, job_id: str, success_count: int, total_count: int):
		"""
		Emit metric for crawl success rate.

		Args:
			job_id: Job ID
			success_count: Number of successful crawls
			total_count: Total number of crawls attempted
		"""
		if total_count > 0:
			success_rate = (success_count / total_count) * 100
			dimensions = [{'Name': 'JobId', 'Value': job_id}]

			self.put_metric('CrawlSuccessRate', success_rate, 'Percent', dimensions)

	def emit_job_created(self, job_id: str, url_count: int):
		"""
		Emit metrics when a job is created.

		Args:
			job_id: Job ID
			url_count: Number of URLs in the job
		"""
		dimensions = [{'Name': 'JobId', 'Value': job_id}]

		self.put_metric('JobCreated', 1, 'Count', dimensions)
		self.put_metric('JobUrlCount', url_count, 'Count', dimensions)

	def emit_query_execution(self, job_id: str, query_type: str, duration_ms: float, result_count: int):
		"""
		Emit metrics for query execution.

		Args:
			job_id: Job ID
			query_type: Type of query (xpath, regex, jsonpath)
			duration_ms: Query execution duration
			result_count: Number of results returned
		"""
		dimensions = [
			{'Name': 'JobId', 'Value': job_id},
			{'Name': 'QueryType', 'Value': query_type}
		]

		self.put_metric('QueryExecutionDuration', duration_ms, 'Milliseconds', dimensions)
		self.put_metric('QueryResultCount', result_count, 'Count', dimensions)

	def emit_s3_upload(self, job_id: str, file_size_bytes: int, duration_ms: float):
		"""
		Emit metrics for S3 upload operations.

		Args:
			job_id: Job ID
			file_size_bytes: Size of uploaded file
			duration_ms: Upload duration
		"""
		dimensions = [{'Name': 'JobId', 'Value': job_id}]

		self.put_metric('S3UploadSize', file_size_bytes, 'Bytes', dimensions)
		self.put_metric('S3UploadDuration', duration_ms, 'Milliseconds', dimensions)

	def emit_batch_metrics(self, metrics: List[Dict]):
		"""
		Emit multiple metrics in a single API call for efficiency.

		Args:
			metrics: List of metric dictionaries with keys: name, value, unit, dimensions
		"""
		try:
			metric_data = []

			for metric in metrics[:20]:  # CloudWatch limit is 20 metrics per call
				data = {
					'MetricName': metric['name'],
					'Value': metric['value'],
					'Unit': metric.get('unit', 'None'),
					'Timestamp': datetime.now(timezone.utc)
				}

				if 'dimensions' in metric:
					data['Dimensions'] = metric['dimensions']

				metric_data.append(data)

			if metric_data:
				self.cloudwatch.put_metric_data(
					Namespace=self.namespace,
					MetricData=metric_data
				)
		except Exception as e:
			logger.warning("Failed to emit batch metrics", error=str(e))


# Singleton instance
_metrics_emitter = None


def get_metrics_emitter() -> MetricsEmitter:
	"""Get or create MetricsEmitter singleton."""
	global _metrics_emitter
	if _metrics_emitter is None:
		_metrics_emitter = MetricsEmitter()
	return _metrics_emitter

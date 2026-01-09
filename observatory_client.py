"""
Observatory Client for Snowglobe Integration.
Sends health status, metrics, and events to the Snowglobe Observatory dashboard.
"""

import os
import requests
from typing import Dict, Any, Literal, Optional
from datetime import datetime, timezone


class ObservatoryClient:
	"""
	Lightweight client for reporting to Snowglobe Observatory.

	Provides non-blocking integration with the centralized monitoring dashboard,
	allowing snowscrape to report health status, metrics, and events without
	affecting the main application flow.
	"""

	def __init__(
		self,
		url: Optional[str] = None,
		api_key: Optional[str] = None,
		site_id: Optional[str] = None
	):
		"""
		Initialize Observatory client.

		Args:
			url: Observatory URL (defaults to env SNOWGLOBE_URL)
			api_key: API key for authentication (defaults to env SNOWGLOBE_API_KEY)
			site_id: Unique site identifier (defaults to env SNOWGLOBE_SITE_ID)
		"""
		self.url = url or os.getenv('SNOWGLOBE_URL', 'https://snowglobe.alexdiaz.me')
		self.api_key = api_key or os.getenv('SNOWGLOBE_API_KEY')
		self.site_id = site_id or os.getenv('SNOWGLOBE_SITE_ID', 'snowscrape')
		self.enabled = bool(self.api_key)  # Only enabled if API key is set

	def _make_request(
		self,
		endpoint: str,
		data: Dict[str, Any],
		timeout: int = 5
	) -> bool:
		"""
		Make HTTP request to Observatory API.

		Args:
			endpoint: API endpoint path
			data: Request payload
			timeout: Request timeout in seconds

		Returns:
			True if successful, False otherwise
		"""
		if not self.enabled:
			return False

		try:
			response = requests.post(
				f'{self.url}{endpoint}',
				headers={
					'x-api-key': self.api_key,
					'Content-Type': 'application/json'
				},
				json=data,
				timeout=timeout
			)
			response.raise_for_status()
			return True
		except requests.exceptions.Timeout:
			print(f'Observatory request timed out: {endpoint}')
			return False
		except requests.exceptions.RequestException as e:
			print(f'Observatory request failed: {endpoint} - {str(e)}')
			return False
		except Exception as e:
			print(f'Unexpected error reporting to Observatory: {str(e)}')
			return False

	def report_health(
		self,
		status: Literal['healthy', 'degraded', 'down'],
		response_time_ms: Optional[int] = None,
		error: Optional[str] = None
	) -> bool:
		"""
		Report health status to Observatory.

		Args:
			status: Health status (healthy, degraded, or down)
			response_time_ms: Health check response time in milliseconds
			error: Error message if status is degraded or down

		Returns:
			True if reported successfully, False otherwise

		Example:
			observatory.report_health('healthy', response_time_ms=42)
			observatory.report_health('down', error='Database unreachable')
		"""
		data = {
			'status': status,
			'timestamp': datetime.now(timezone.utc).isoformat()
		}

		if response_time_ms is not None:
			data['responseTimeMs'] = response_time_ms

		if error:
			data['error'] = error

		return self._make_request(
			f'/api/sites/{self.site_id}/health',
			data
		)

	def send_metrics(self, metrics: Dict[str, Any]) -> bool:
		"""
		Send custom metrics to Observatory.

		Args:
			metrics: Dictionary of metric name-value pairs

		Returns:
			True if sent successfully, False otherwise

		Example:
			observatory.send_metrics({
				'jobsProcessed': 150,
				'successRate': 98.5,
				'avgCrawlDuration': 2500,
				'activeJobs': 5
			})
		"""
		data = {
			'siteId': self.site_id,
			'metrics': metrics,
			'timestamp': datetime.now(timezone.utc).isoformat()
		}

		return self._make_request('/api/metrics', data)

	def track_event(
		self,
		event_type: str,
		data: Optional[Dict[str, Any]] = None
	) -> bool:
		"""
		Track an event in Observatory.

		Args:
			event_type: Type of event (e.g., 'deployment', 'error', 'milestone')
			data: Optional event metadata

		Returns:
			True if tracked successfully, False otherwise

		Example:
			observatory.track_event('deployment', {
				'version': '1.2.0',
				'environment': 'production'
			})
			observatory.track_event('critical_error', {
				'error': 'DLQ threshold exceeded',
				'count': 10
			})
		"""
		payload = {
			'siteId': self.site_id,
			'eventType': event_type,
			'timestamp': datetime.now(timezone.utc).isoformat()
		}

		if data:
			payload['data'] = data

		return self._make_request('/api/events', payload)

	def register(
		self,
		name: str,
		site_type: Literal['site', 'app', 'api', 'pipeline', 'tool', 'database'],
		**kwargs
	) -> bool:
		"""
		Register or update site information in Observatory.

		Args:
			name: Display name for the site
			site_type: Type of service
			**kwargs: Additional metadata (platform, domain, repository, etc.)

		Returns:
			True if registered successfully, False otherwise

		Example:
			observatory.register(
				name='Snowscrape',
				site_type='pipeline',
				platform='AWS Lambda',
				repository='https://github.com/user/snowscrape',
				healthEndpoint='https://api.snowscrape.com/health',
				version='1.0.0',
				databases=['DynamoDB'],
				services=['S3', 'SQS']
			)
		"""
		data = {
			'siteId': self.site_id,
			'name': name,
			'type': site_type,
			**kwargs
		}

		return self._make_request('/api/sites', data)

	def send_batch_metrics(
		self,
		jobs_processed: int,
		jobs_completed: int,
		jobs_failed: int,
		success_rate: float,
		avg_crawl_duration_ms: float,
		active_jobs: int,
		queue_depth: int,
		urls_crawled: int,
		error_rate: float
	) -> bool:
		"""
		Convenience method to send standard batch of snowscrape metrics.

		Args:
			jobs_processed: Total jobs processed in period
			jobs_completed: Jobs completed successfully
			jobs_failed: Jobs that failed
			success_rate: Success rate percentage (0-100)
			avg_crawl_duration_ms: Average crawl duration in milliseconds
			active_jobs: Currently active/processing jobs
			queue_depth: Number of jobs in SQS queue
			urls_crawled: Total URLs crawled in period
			error_rate: Error rate percentage (0-100)

		Returns:
			True if sent successfully, False otherwise
		"""
		return self.send_metrics({
			'jobsProcessed': jobs_processed,
			'jobsCompleted': jobs_completed,
			'jobsFailed': jobs_failed,
			'successRate': round(success_rate, 2),
			'avgCrawlDurationMs': round(avg_crawl_duration_ms, 2),
			'activeJobs': active_jobs,
			'queueDepth': queue_depth,
			'urlsCrawled': urls_crawled,
			'errorRate': round(error_rate, 2)
		})


# Singleton instance for module-level access
_observatory_client = None


def get_observatory_client() -> ObservatoryClient:
	"""Get or create Observatory client singleton."""
	global _observatory_client
	if _observatory_client is None:
		_observatory_client = ObservatoryClient()
	return _observatory_client

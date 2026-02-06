"""
Snowglobe Analytics Client for Python
Sends events, metrics, and health status to the Snowglobe Observatory
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import urllib.request
import urllib.error
from logger import get_logger

logger = get_logger(__name__)

# Configuration from environment
SNOWGLOBE_URL = os.environ.get("SNOWGLOBE_URL", "https://snowglobe.alexdiaz.me")
SNOWGLOBE_API_KEY = os.environ.get("SNOWGLOBE_API_KEY", "")
SNOWGLOBE_SITE_ID = os.environ.get("SNOWGLOBE_SITE_ID", "snowscrape")
SNOWGLOBE_ENABLED = bool(SNOWGLOBE_API_KEY)


def _make_request(
    endpoint: str, method: str = "POST", data: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Make a request to the Snowglobe API."""
    if not SNOWGLOBE_ENABLED:
        return None

    url = f"{SNOWGLOBE_URL}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": SNOWGLOBE_API_KEY,
    }

    try:
        request_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        logger.warning("Snowglobe request failed", error=str(e))
        return None
    except Exception as e:
        logger.error("Snowglobe request error", error=str(e))
        return None


def track_event(event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Track an analytics event."""
    _make_request(
        "/api/events",
        "POST",
        {
            "siteId": SNOWGLOBE_SITE_ID,
            "eventType": event_type,
            "data": {
                **(data or {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


def report_health(
    status: str,  # "healthy", "degraded", or "down"
    response_time_ms: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """Report health status to Snowglobe."""
    details = {}
    if response_time_ms is not None:
        details["responseTimeMs"] = response_time_ms
    if error is not None:
        details["error"] = error

    _make_request(
        f"/api/sites/{SNOWGLOBE_SITE_ID}/health",
        "POST",
        {"status": status, **details},
    )


def send_metrics(metrics: Dict[str, Any]) -> None:
    """Send metrics snapshot to Snowglobe."""
    _make_request(
        "/api/metrics",
        "POST",
        {
            "siteId": SNOWGLOBE_SITE_ID,
            "metrics": metrics,
        },
    )


def register_site() -> None:
    """Register this site with Snowglobe."""
    _make_request(
        "/api/sites",
        "POST",
        {
            "siteId": SNOWGLOBE_SITE_ID,
            "name": "Snowscrape",
            "type": "tool",
            "platform": "AWS Lambda",
            "domain": "snowscrape.alexdiaz.me",
            "repository": "snowthen-o7/snowscrape",
            "description": "Web scraping and data collection tool",
            "databases": ["DynamoDB", "S3"],
            "services": ["AWS Lambda", "SQS", "Clerk"],
        },
    )


def report_job_completed(
    job_id: str,
    urls_processed: int,
    success_count: int,
    error_count: int,
    duration_ms: int,
) -> None:
    """Report a completed job to Snowglobe."""
    track_event(
        "job_completed",
        {
            "job_id": job_id,
            "urls_processed": urls_processed,
            "success_count": success_count,
            "error_count": error_count,
            "duration_ms": duration_ms,
        },
    )


def report_job_failed(job_id: str, error: str) -> None:
    """Report a failed job to Snowglobe."""
    track_event(
        "job_failed",
        {
            "job_id": job_id,
            "error": error,
        },
    )

"""
Domain Rate Limiter

Enforces minimum delay between requests to the same domain to avoid
triggering bot protection and overwhelming target servers.

Since Lambda functions are stateless, this uses an in-memory approach
per invocation -- each Lambda processes a batch of URLs with rate
limiting applied within that batch.
"""

import time
from collections import defaultdict
from urllib.parse import urlparse
from logger import get_logger

logger = get_logger(__name__)

# Default delay in seconds between requests to the same domain
DEFAULT_MIN_DELAY = 1.0


class DomainRateLimiter:
    """
    Enforces minimum delay between requests to the same domain.

    Tracks the last request time per domain and blocks (via sleep) until
    the configured delay has elapsed before allowing the next request.

    Args:
        min_delay: Minimum seconds between requests to the same domain.
                   Defaults to 1.0 second.
    """

    def __init__(self, min_delay: float = DEFAULT_MIN_DELAY):
        if min_delay < 0:
            raise ValueError("min_delay must be non-negative")
        self.min_delay = min_delay
        self._last_request_time: dict[str, float] = defaultdict(float)

    @staticmethod
    def get_domain(url: str) -> str:
        """Extract the domain (netloc) from a URL."""
        return urlparse(url).netloc

    def wait_if_needed(self, url: str) -> float:
        """
        Block until it is safe to make a request to this URL's domain.

        If the minimum delay has not yet elapsed since the last request
        to the same domain, this method sleeps for the remaining time.

        Args:
            url: The target URL about to be requested.

        Returns:
            The number of seconds actually waited (0.0 if no wait was needed).
        """
        if self.min_delay <= 0:
            return 0.0

        domain = self.get_domain(url)
        now = time.time()
        elapsed = now - self._last_request_time[domain]
        wait_time = 0.0

        if elapsed < self.min_delay:
            wait_time = self.min_delay - elapsed
            logger.debug(
                "Rate limiting: waiting before next request",
                domain=domain,
                wait_seconds=round(wait_time, 3),
            )
            time.sleep(wait_time)

        self._last_request_time[domain] = time.time()
        return wait_time

    def reset(self, domain: str = None) -> None:
        """
        Reset rate limit tracking.

        Args:
            domain: If provided, reset only this domain. Otherwise reset all.
        """
        if domain:
            self._last_request_time.pop(domain, None)
        else:
            self._last_request_time.clear()

"""
AWS Proxy Pool Manager
Manages a pool of EC2-based Squid proxies for web scraping.
"""

import boto3
import json
import os
import random
from typing import Dict, List, Optional
from logger import get_logger

logger = get_logger(__name__)

secrets_client = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')


class AWSProxyManager:
    """Manages AWS-based proxy pool with health checking and rotation."""

    def __init__(self):
        self.proxy_table = dynamodb.Table(os.environ.get('DYNAMODB_PROXY_POOL_TABLE', 'SnowscrapeProxyPool'))
        self._proxy_pool = None
        self._proxy_pool_timestamp = 0
        self._cache_ttl = 300  # Cache for 5 minutes

    def get_proxy_pool(self) -> List[Dict]:
        """
        Load proxy pool from Secrets Manager with caching.

        Returns:
            List of proxy dictionaries with url, region, status, etc.
        """
        import time
        current_time = time.time()

        # Return cached data if still valid
        if self._proxy_pool and (current_time - self._proxy_pool_timestamp) < self._cache_ttl:
            return self._proxy_pool

        try:
            # Fetch from Secrets Manager
            secret = secrets_client.get_secret_value(
                SecretId='snowscrape/proxy-pool'
            )

            secret_data = json.loads(secret['SecretString'])
            proxies = secret_data.get('proxies', [])

            logger.info("Loaded proxy pool from Secrets Manager", proxy_count=len(proxies))

            # Update cache
            self._proxy_pool = proxies
            self._proxy_pool_timestamp = current_time

            return proxies

        except Exception as e:
            logger.error("Failed to load proxy pool from Secrets Manager", error=str(e))
            # Return cached data even if expired, or empty list
            return self._proxy_pool if self._proxy_pool else []

    def get_proxy_url(self, proxy_config: Dict) -> Optional[str]:
        """
        Get a proxy URL based on configuration.

        Args:
            proxy_config: Configuration dict with:
                - geo_targeting: 'us', 'eu', 'as', or 'any'
                - rotation_strategy: 'random' or 'round-robin'
                - fallback_to_direct: bool

        Returns:
            Proxy URL with credentials, or None if no proxy available
        """
        if not proxy_config or not proxy_config.get('enabled'):
            return None

        proxies = self.get_proxy_pool()

        if not proxies:
            logger.warning("No proxies available in pool")
            return None

        # Filter by geo-targeting
        geo = proxy_config.get('geo_targeting', 'any')
        if geo != 'any':
            region_map = {
                'us': ['us-east-1', 'us-west-2'],
                'eu': ['eu-west-1'],
                'as': ['ap-southeast-1', 'ap-southeast-2']
            }
            target_regions = region_map.get(geo, [])
            proxies = [p for p in proxies if p.get('region') in target_regions and p.get('status') == 'healthy']
        else:
            proxies = [p for p in proxies if p.get('status') == 'healthy']

        if not proxies:
            logger.warning("No healthy proxies available", geo_targeting=geo)
            if proxy_config.get('fallback_to_direct', True):
                logger.info("Falling back to direct connection")
                return None
            else:
                raise Exception(f"No healthy proxies available for geo-targeting: {geo}")

        # Select proxy based on rotation strategy
        rotation = proxy_config.get('rotation_strategy', 'random')
        if rotation == 'random':
            proxy = random.choice(proxies)
        elif rotation == 'round-robin':
            proxy = self._get_round_robin_proxy(proxies)
        else:
            proxy = proxies[0]

        proxy_url = proxy['url']
        logger.info(
            "Selected proxy",
            proxy_url=self._mask_proxy_url(proxy_url),
            region=proxy.get('region'),
            rotation=rotation
        )

        return proxy_url

    def _get_round_robin_proxy(self, proxies: List[Dict]) -> Dict:
        """
        Simple round-robin proxy selection.
        Tracks usage in DynamoDB to ensure even distribution.

        Args:
            proxies: List of available proxies

        Returns:
            Selected proxy dict
        """
        try:
            # Get usage stats for all proxies
            proxy_usage = {}
            for proxy in proxies:
                proxy_id = self._get_proxy_id(proxy['url'])
                try:
                    response = self.proxy_table.get_item(Key={'proxy_id': proxy_id})
                    if 'Item' in response:
                        proxy_usage[proxy_id] = response['Item'].get('request_count', 0)
                    else:
                        proxy_usage[proxy_id] = 0
                except Exception:
                    proxy_usage[proxy_id] = 0

            # Select proxy with lowest usage
            min_usage_proxy_id = min(proxy_usage, key=proxy_usage.get)
            selected_proxy = next(p for p in proxies if self._get_proxy_id(p['url']) == min_usage_proxy_id)

            return selected_proxy

        except Exception as e:
            logger.warning("Round-robin selection failed, falling back to random", error=str(e))
            return random.choice(proxies)

    def track_usage(self, proxy_url: str, success: bool, bytes_transferred: int = 0):
        """
        Track proxy usage statistics.

        Args:
            proxy_url: Proxy URL that was used
            success: Whether the request succeeded
            bytes_transferred: Number of bytes transferred
        """
        try:
            proxy_id = self._get_proxy_id(proxy_url)

            # Update DynamoDB with usage stats
            self.proxy_table.update_item(
                Key={'proxy_id': proxy_id},
                UpdateExpression="""
                    SET request_count = if_not_exists(request_count, :zero) + :one,
                        bytes_transferred = if_not_exists(bytes_transferred, :zero) + :bytes,
                        failed_requests = if_not_exists(failed_requests, :zero) + :failed,
                        last_used = :now
                """,
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':one': 1,
                    ':bytes': bytes_transferred,
                    ':failed': 0 if success else 1,
                    ':now': int(__import__('time').time())
                }
            )

            # Emit CloudWatch metric
            cloudwatch.put_metric_data(
                Namespace='SnowScrape/Proxies',
                MetricData=[
                    {
                        'MetricName': 'BytesTransferred',
                        'Value': bytes_transferred,
                        'Unit': 'Bytes',
                        'Dimensions': [{'Name': 'ProxyID', 'Value': proxy_id}]
                    },
                    {
                        'MetricName': 'RequestCount',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [{'Name': 'ProxyID', 'Value': proxy_id}]
                    },
                    {
                        'MetricName': 'FailedRequests' if not success else 'SuccessfulRequests',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [{'Name': 'ProxyID', 'Value': proxy_id}]
                    }
                ]
            )

            logger.debug("Proxy usage tracked", proxy_id=proxy_id, success=success, bytes=bytes_transferred)

        except Exception as e:
            logger.warning("Failed to track proxy usage", error=str(e))

    def mark_proxy_failed(self, proxy_url: str, error: str):
        """
        Mark a proxy as temporarily failed.
        This will be picked up by the health checker.

        Args:
            proxy_url: Proxy URL that failed
            error: Error message
        """
        try:
            proxy_id = self._get_proxy_id(proxy_url)

            self.proxy_table.update_item(
                Key={'proxy_id': proxy_id},
                UpdateExpression="""
                    SET consecutive_failures = if_not_exists(consecutive_failures, :zero) + :one,
                        last_error = :error,
                        last_failure_time = :now
                """,
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':one': 1,
                    ':error': error,
                    ':now': int(__import__('time').time())
                }
            )

            logger.warning("Proxy marked as failed", proxy_id=proxy_id, error=error)

        except Exception as e:
            logger.error("Failed to mark proxy as failed", error=str(e))

    def get_proxy_stats(self) -> List[Dict]:
        """
        Get usage statistics for all proxies.

        Returns:
            List of proxy stats
        """
        try:
            response = self.proxy_table.scan()
            items = response.get('Items', [])

            stats = []
            for item in items:
                stats.append({
                    'proxy_id': item['proxy_id'],
                    'request_count': item.get('request_count', 0),
                    'bytes_transferred': item.get('bytes_transferred', 0),
                    'failed_requests': item.get('failed_requests', 0),
                    'consecutive_failures': item.get('consecutive_failures', 0),
                    'last_used': item.get('last_used'),
                    'last_error': item.get('last_error')
                })

            return stats

        except Exception as e:
            logger.error("Failed to get proxy stats", error=str(e))
            return []

    @staticmethod
    def _get_proxy_id(proxy_url: str) -> str:
        """Extract proxy ID (IP address) from proxy URL."""
        # Extract IP from URL like http://user:pass@1.2.3.4:3128
        import re
        match = re.search(r'@([\d.]+):', proxy_url)
        if match:
            return match.group(1)
        return proxy_url

    @staticmethod
    def _mask_proxy_url(proxy_url: str) -> str:
        """Mask credentials in proxy URL for logging."""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', proxy_url)


# Singleton instance
_proxy_manager = None


def get_proxy_manager() -> AWSProxyManager:
    """Get singleton proxy manager instance."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = AWSProxyManager()
    return _proxy_manager

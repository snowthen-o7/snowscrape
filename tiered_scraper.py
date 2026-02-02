"""
Tiered Scraping System
Smart tier escalation for cost-effective bot protection bypass.

Tier 1: Lightweight (requests + BeautifulSoup) - Default
Tier 2: IP Rotation (Tier 1 + residential proxy)
Tier 3: Browser (Playwright + stealth + proxy)
Tier 4: CAPTCHA Solving (Tier 3 + 2Captcha)
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Tuple, Optional
from logger import get_logger
import re
import urllib3

# Suppress SSL warnings when using proxies (they do SSL interception)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)


# Tier definitions and costs
TIER_INFO = {
    1: {
        'name': 'Lightweight',
        'description': 'Fast requests-based scraping',
        'cost_per_page': 0.0001,
        'avg_time_seconds': 2,
    },
    2: {
        'name': 'IP Rotation',
        'description': 'Residential proxy for IP-based blocking',
        'cost_per_page': 0.005,
        'avg_time_seconds': 4,
    },
    3: {
        'name': 'Browser Mode',
        'description': 'Full headless browser with stealth',
        'cost_per_page': 0.08,
        'avg_time_seconds': 12,
    },
    4: {
        'name': 'CAPTCHA Solving',
        'description': 'Browser + automatic CAPTCHA solving',
        'cost_per_page': 0.15,
        'avg_time_seconds': 25,
    },
}


class BlockingDetectionError(Exception):
    """Raised when blocking is detected."""
    def __init__(self, message: str, tier_used: int, indicators: List[str]):
        super().__init__(message)
        self.tier_used = tier_used
        self.indicators = indicators


def detect_blocking(response: requests.Response, content: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Detect if we've been blocked by bot protection.

    Uses conservative detection to avoid false positives. Only flags actual blocking,
    not just presence of security libraries in normal pages.

    Args:
        response: The HTTP response object
        content: Optional page content (for BeautifulSoup parsed content)

    Returns:
        Tuple of (is_blocked: bool, indicators: List[str])
    """
    indicators = []
    text_to_check = content if content else (response.text if hasattr(response, 'text') else '')

    # Check 1: HTTP status codes - STRONG indicators of blocking
    if hasattr(response, 'status_code'):
        if response.status_code == 403:
            indicators.append('403_forbidden')
        elif response.status_code == 429:
            indicators.append('429_rate_limited')
        elif response.status_code == 503:
            indicators.append('503_service_unavailable')

    # Check 2: Content-based detection - ONLY check for actual challenge pages
    # Don't check for generic keywords like "captcha" or "cloudflare" since many
    # normal pages include these in their scripts/libraries
    if text_to_check:
        text_lower = text_to_check.lower()

        # Very specific patterns that indicate actual challenge/block pages
        blocking_patterns = [
            # Cloudflare challenge pages
            ('just a moment...', 'cloudflare_challenge'),
            ('checking your browser', 'cloudflare_challenge'),
            ('enable javascript and cookies', 'cloudflare_challenge'),
            ('cf-browser-verification', 'cloudflare_verification'),

            # Generic access denial messages
            ('access denied', 'access_denied'),
            ('access forbidden', 'access_forbidden'),

            # Human verification prompts (these appear in challenge pages, not normal pages)
            ('verify you are human', 'human_verification'),
            ('prove you are human', 'human_verification'),
            ('unusual traffic from your computer network', 'unusual_traffic'),
            ('automated access', 'automation_detected'),
            ('please complete the security check', 'security_check'),

            # Specific bot protection services (in challenge pages, not just scripts)
            ('perimeterpx', 'perimeterx_challenge'),
            ('datadome', 'datadome_challenge'),
        ]

        for pattern, indicator_name in blocking_patterns:
            if pattern in text_lower:
                indicators.append(indicator_name)

    # Check 3: Very minimal content (likely error page or redirect)
    # Increased threshold to 200 to avoid false positives on legitimate minimal pages
    if text_to_check and len(text_to_check.strip()) < 200:
        # Only flag if combined with suspicious status or content
        if indicators or (hasattr(response, 'status_code') and response.status_code >= 400):
            indicators.append('minimal_content')

    is_blocked = len(indicators) > 0

    if is_blocked:
        logger.warning("Blocking detected", indicators=indicators)

    return is_blocked, indicators


def scrape_tier_1(url: str, timeout: int = 35) -> Dict[str, Any]:
    """
    Tier 1: Lightweight scraping with requests + BeautifulSoup.

    Args:
        url: Target URL to scrape
        timeout: Request timeout in seconds

    Returns:
        Dictionary with page data and metadata

    Raises:
        BlockingDetectionError: If blocking is detected
        requests.RequestException: For network errors
    """
    logger.info("Attempting Tier 1 (Lightweight) scraping", url=url)

    # Browser-like headers (same as current implementation)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

    response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

    # Check for blocking
    is_blocked, indicators = detect_blocking(response)

    if is_blocked:
        raise BlockingDetectionError(
            f"Tier 1 blocked: {', '.join(indicators)}",
            tier_used=1,
            indicators=indicators
        )

    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    return {
        'status_code': response.status_code,
        'content': response.content,
        'text': response.text,
        'soup': soup,
        'url': response.url,
        'headers': dict(response.headers),
        'tier_used': 1,
        'tier_name': TIER_INFO[1]['name'],
        'cost': TIER_INFO[1]['cost_per_page'],
    }


def scrape_tier_2(url: str, proxy_config: Optional[Dict[str, str]] = None, timeout: int = 40) -> Dict[str, Any]:
    """
    Tier 2: IP Rotation using residential proxies.

    Supports two proxy modes:
    1. Residential proxy service (Bright Data, Oxylabs, etc.) via RESIDENTIAL_PROXY_URL env var
    2. AWS EC2 proxy pool via existing proxy_manager infrastructure

    Args:
        url: Target URL to scrape
        proxy_config: Proxy configuration (http/https proxy URLs)
        timeout: Request timeout in seconds

    Returns:
        Dictionary with page data and metadata

    Raises:
        BlockingDetectionError: If blocking is detected
        requests.RequestException: For network errors
    """
    import os
    logger.info("Attempting Tier 2 (IP Rotation) scraping", url=url, has_proxy=bool(proxy_config))

    # Determine proxy URL to use
    proxy_url = None

    # Option 1: Use provided proxy_config
    if proxy_config and (proxy_config.get('http') or proxy_config.get('https')):
        proxy_url = proxy_config.get('https') or proxy_config.get('http')
        logger.info("Using provided proxy config")

    # Option 2: Use residential proxy from environment variable
    elif os.environ.get('RESIDENTIAL_PROXY_URL'):
        proxy_url = os.environ.get('RESIDENTIAL_PROXY_URL')
        logger.info("Using residential proxy from environment")

    # Option 3: Try AWS proxy pool (existing infrastructure)
    else:
        try:
            from proxy_manager import get_proxy_manager
            proxy_manager = get_proxy_manager()
            aws_proxy_config = {
                'enabled': True,
                'geo_targeting': 'any',
                'rotation_strategy': 'random',
                'fallback_to_direct': False
            }
            proxy_url = proxy_manager.get_proxy_url(aws_proxy_config)
            if proxy_url:
                logger.info("Using AWS proxy pool")
        except Exception as e:
            logger.warning("AWS proxy pool not available", error=str(e))

    # If no proxy available, fail with helpful message
    if not proxy_url:
        raise NotImplementedError(
            "Tier 2 (Proxy) requires proxy configuration. "
            "Set RESIDENTIAL_PROXY_URL environment variable or configure AWS proxy pool. "
            "Sign up for Bright Data (https://brightdata.com) or Oxylabs for residential proxies."
        )

    # Use same headers as Tier 1 (browser-like)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

    # Configure proxies dict for requests
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }

    try:
        # Disable SSL verification when using proxies (they do SSL interception)
        # This is standard practice for residential proxy services
        response = requests.get(
            url,
            headers=headers,
            proxies=proxies,
            timeout=timeout,
            allow_redirects=True,
            verify=False  # Required for proxy SSL interception
        )

        # Check for blocking even with proxy
        is_blocked, indicators = detect_blocking(response)

        if is_blocked:
            raise BlockingDetectionError(
                f"Tier 2 blocked even with proxy: {', '.join(indicators)}",
                tier_used=2,
                indicators=indicators
            )

        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        logger.info("Tier 2 scraping successful", url=url, proxy_used=bool(proxy_url))

        return {
            'status_code': response.status_code,
            'content': response.content,
            'text': response.text,
            'soup': soup,
            'url': response.url,
            'headers': dict(response.headers),
            'tier_used': 2,
            'tier_name': TIER_INFO[2]['name'],
            'cost': TIER_INFO[2]['cost_per_page'],
        }

    except BlockingDetectionError:
        # Re-raise blocking errors for escalation
        raise
    except Exception as e:
        logger.error("Tier 2 proxy request failed", url=url, error=str(e))
        # Re-raise for potential escalation to Tier 3
        raise


def scrape_tier_3(url: str, proxy_config: Optional[Dict[str, str]] = None, timeout: int = 45) -> Dict[str, Any]:
    """
    Tier 3: Browser-based scraping with Playwright.

    Args:
        url: Target URL to scrape
        proxy_config: Proxy configuration for browser
        timeout: Request timeout in seconds

    Returns:
        Dictionary with page data and metadata

    Raises:
        BlockingDetectionError: If blocking is detected
    """
    logger.info("Attempting Tier 3 (Browser Mode) scraping", url=url)

    # TODO: Week 2 implementation
    raise NotImplementedError("Tier 3 (Browser) not yet implemented. Coming in Week 2.")


def scrape_tier_4(url: str, proxy_config: Optional[Dict[str, str]] = None, timeout: int = 60) -> Dict[str, Any]:
    """
    Tier 4: Browser + CAPTCHA solving.

    Args:
        url: Target URL to scrape
        proxy_config: Proxy configuration for browser
        timeout: Request timeout in seconds

    Returns:
        Dictionary with page data and metadata
    """
    logger.info("Attempting Tier 4 (CAPTCHA Solving) scraping", url=url)

    # TODO: Week 3 implementation
    raise NotImplementedError("Tier 4 (CAPTCHA) not yet implemented. Coming in Week 3.")


async def smart_scrape(
    url: str,
    min_tier: int = 1,
    max_tier: int = 4,
    auto_escalate: bool = True,
    proxy_config: Optional[Dict[str, str]] = None,
    timeout: int = 40
) -> Tuple[Dict[str, Any], int, List[str]]:
    """
    Smart scraping with automatic tier escalation.

    Args:
        url: Target URL to scrape
        min_tier: Minimum tier to start with (1-4)
        max_tier: Maximum tier to allow (1-4)
        auto_escalate: Whether to automatically escalate on blocking
        proxy_config: Proxy configuration (for Tier 2+)
        timeout: Request timeout in seconds

    Returns:
        Tuple of (result_data, tier_used, escalation_log)

    Raises:
        Exception: If all tiers fail
    """
    escalation_log = []
    current_tier = min_tier

    tier_functions = {
        1: scrape_tier_1,
        2: scrape_tier_2,
        3: scrape_tier_3,
        4: scrape_tier_4,
    }

    while current_tier <= max_tier:
        tier_name = TIER_INFO[current_tier]['name']
        escalation_log.append(f"Attempting Tier {current_tier} ({tier_name})")

        try:
            # Get the appropriate scraping function
            scrape_func = tier_functions[current_tier]

            # Call it with appropriate parameters
            if current_tier == 1:
                result = scrape_func(url, timeout=timeout)
            else:
                result = scrape_func(url, proxy_config=proxy_config, timeout=timeout)

            # Success!
            escalation_log.append(f"✅ Success with Tier {current_tier}")
            logger.info(
                "Scraping successful",
                url=url,
                tier=current_tier,
                tier_name=tier_name,
                cost=TIER_INFO[current_tier]['cost_per_page']
            )

            return result, current_tier, escalation_log

        except BlockingDetectionError as e:
            escalation_log.append(f"❌ Tier {current_tier} blocked: {', '.join(e.indicators)}")
            logger.warning(
                "Tier blocked, escalating",
                tier=current_tier,
                indicators=e.indicators,
                auto_escalate=auto_escalate
            )

            if not auto_escalate or current_tier >= max_tier:
                # Don't escalate, or we've hit the max
                raise Exception(f"Scraping failed at Tier {current_tier}: {str(e)}")

            # Escalate to next tier
            current_tier += 1
            escalation_log.append(f"⬆️ Escalating to Tier {current_tier}")

        except NotImplementedError as e:
            # Tier not implemented yet - don't escalate, fail with helpful message
            escalation_log.append(f"⚠️ Tier {current_tier} not implemented: {str(e)}")

            # Build helpful error message
            error_msg = (
                f"This site requires Tier {current_tier} ({tier_name}) which is not yet implemented. "
                f"{str(e)} "
            )

            if current_tier == 2:
                error_msg += "Proxy integration is planned for Week 1."
            elif current_tier == 3:
                error_msg += "Browser mode is planned for Week 2."
            elif current_tier == 4:
                error_msg += "CAPTCHA solving is planned for Week 3."

            raise Exception(error_msg)

        except Exception as e:
            escalation_log.append(f"❌ Tier {current_tier} error: {str(e)}")
            logger.error(
                "Tier failed with error",
                tier=current_tier,
                error=str(e)
            )

            if not auto_escalate or current_tier >= max_tier:
                raise

            # Escalate to next tier
            current_tier += 1
            escalation_log.append(f"⬆️ Escalating to Tier {current_tier} after error")

    # If we get here, all tiers failed
    raise Exception(f"All tiers exhausted (1-{max_tier}). Scraping failed.")


def get_tier_info(tier: int) -> Dict[str, Any]:
    """Get information about a specific tier."""
    return TIER_INFO.get(tier, {})


def estimate_cost(tier: int, num_pages: int) -> float:
    """Estimate cost for scraping N pages at a given tier."""
    tier_data = TIER_INFO.get(tier, {})
    cost_per_page = tier_data.get('cost_per_page', 0)
    return cost_per_page * num_pages

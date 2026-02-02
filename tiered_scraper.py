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

    Args:
        response: The HTTP response object
        content: Optional page content (for BeautifulSoup parsed content)

    Returns:
        Tuple of (is_blocked: bool, indicators: List[str])
    """
    indicators = []
    text_to_check = content if content else (response.text if hasattr(response, 'text') else '')

    # Check 1: HTTP status codes
    if hasattr(response, 'status_code'):
        if response.status_code == 403:
            indicators.append('403_forbidden')
        elif response.status_code == 429:
            indicators.append('429_rate_limited')
        elif response.status_code == 503:
            indicators.append('503_service_unavailable')

    # Check 2: Content-based detection
    if text_to_check:
        text_lower = text_to_check.lower()

        blocking_patterns = [
            ('captcha', 'captcha_detected'),
            ('recaptcha', 'recaptcha_detected'),
            ('hcaptcha', 'hcaptcha_detected'),
            ('cloudflare', 'cloudflare_challenge'),
            ('access denied', 'access_denied'),
            ('access forbidden', 'access_forbidden'),
            ('unusual traffic', 'unusual_traffic'),
            ('verify you are human', 'human_verification'),
            ('please verify', 'verification_required'),
            ('bot detection', 'bot_detected'),
            ('automated access', 'automation_detected'),
            ('please complete the security check', 'security_check'),
            ('perimeter', 'perimeterx_detected'),
            ('datadome', 'datadome_detected'),
            ('distil', 'distil_detected'),
            ('akamai', 'akamai_detected'),
        ]

        for pattern, indicator_name in blocking_patterns:
            if pattern in text_lower:
                indicators.append(indicator_name)

    # Check 3: Empty or minimal content (suspicious)
    if text_to_check and len(text_to_check.strip()) < 100:
        indicators.append('minimal_content')

    # Check 4: Cloudflare challenge page detection (specific check)
    if text_to_check and 'cf-browser-verification' in text_to_check:
        indicators.append('cloudflare_browser_verification')

    is_blocked = len(indicators) > 0

    if is_blocked:
        logger.warning("Blocking detected", indicators=indicators)

    return is_blocked, indicators


def scrape_tier_1(url: str, timeout: int = 25) -> Dict[str, Any]:
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


def scrape_tier_2(url: str, proxy_config: Optional[Dict[str, str]] = None, timeout: int = 30) -> Dict[str, Any]:
    """
    Tier 2: IP Rotation using residential proxies.

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
    logger.info("Attempting Tier 2 (IP Rotation) scraping", url=url, has_proxy=bool(proxy_config))

    # TODO: For now, this is a placeholder that returns an error
    # Week 1 implementation will add actual proxy integration
    raise NotImplementedError("Tier 2 (Proxy) not yet implemented. Coming in Week 1.")


def scrape_tier_3(url: str, proxy_config: Optional[Dict[str, str]] = None, timeout: int = 30) -> Dict[str, Any]:
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
    timeout: int = 30
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
            # Tier not implemented yet
            escalation_log.append(f"⚠️ Tier {current_tier} not implemented: {str(e)}")

            if not auto_escalate or current_tier >= max_tier:
                raise Exception(f"Tier {current_tier} not available: {str(e)}")

            # Try next tier
            current_tier += 1
            escalation_log.append(f"⬆️ Escalating to Tier {current_tier}")

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

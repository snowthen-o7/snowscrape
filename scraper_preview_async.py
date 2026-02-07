"""
Async Scraper Preview with WebSocket Progress Updates
Handles long-running scraping operations that exceed API Gateway 30s timeout.

Uses Lambda async invocation pattern:
1. scraperPreviewAsyncStart - Returns immediately with task_id, invokes worker Lambda
2. scraperPreviewAsyncWorker - Does actual scraping, sends WebSocket updates
"""

import asyncio
import boto3
import json
import os
import uuid
from typing import Dict, Any
from logger import get_logger
from tiered_scraper import smart_scrape, TIER_INFO
from websocket_handler import broadcast_to_user
from bs4 import BeautifulSoup
from lxml import html as lxml_html

logger = get_logger(__name__)
lambda_client = boto3.client('lambda')


def scrape_with_websocket_updates(
    task_id: str,
    user_id: str,
    url: str,
    timeout: int = 35,
    min_tier: int = 1,
    max_tier: int = 4
):
    """
    Worker function: Scrape a URL and send progress updates via WebSocket.
    This runs in a separate Lambda invocation.

    Args:
        task_id: Unique task identifier
        user_id: User who initiated the scrape
        url: URL to scrape
        timeout: Request timeout in seconds
        min_tier: Minimum tier to start with
        max_tier: Maximum tier to allow
    """
    ws_domain = os.environ.get('WS_API_DOMAIN')
    ws_stage = os.environ.get('WS_API_STAGE', 'dev')

    try:
        # Send initial progress update
        if ws_domain:
            broadcast_to_user(ws_domain, ws_stage, user_id, {
                'type': 'scraper:progress',
                'task_id': task_id,
                'status': 'starting',
                'message': f'Starting scrape for {url}',
                'tier': min_tier
            })

        # Perform the scrape with tier escalation
        logger.info("Starting async scrape", task_id=task_id, url=url, user_id=user_id)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result, tier_used, escalation_log = loop.run_until_complete(
            smart_scrape(
                url=url,
                min_tier=min_tier,
                max_tier=max_tier,
                auto_escalate=True,
                timeout=timeout
            )
        )

        loop.close()

        # Send tier escalation update
        if ws_domain and tier_used > min_tier:
            broadcast_to_user(ws_domain, ws_stage, user_id, {
                'type': 'scraper:progress',
                'task_id': task_id,
                'status': 'escalated',
                'message': f'Escalated to Tier {tier_used} ({TIER_INFO[tier_used]["name"]})',
                'tier': tier_used,
                'tier_name': TIER_INFO[tier_used]['name'],
                'cost_per_page': TIER_INFO[tier_used]['cost_per_page'],
                'escalation_log': escalation_log
            })

        # Extract soup from result
        soup = result.get('soup')
        content = result.get('content') or result.get('text', '')

        if not soup:
            soup = BeautifulSoup(content, 'html.parser')

        # Parse with lxml for better XPath support
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        tree = lxml_html.fromstring(content_bytes)

        # Extract page title
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else url

        # Extract relevant elements (same logic as scraper_preview.py)
        elements = []
        element_id = 0

        selectors = [
            ('h1', soup.find_all('h1')),
            ('h2', soup.find_all('h2')),
            ('h3', soup.find_all('h3')),
            ('h4', soup.find_all('h4')),
            ('h5', soup.find_all('h5')),
            ('h6', soup.find_all('h6')),
            ('p', soup.find_all('p')),
            ('span', soup.find_all('span')),
            ('div', soup.find_all('div')),
            ('a', soup.find_all('a')),
            ('td', soup.find_all('td')),
            ('th', soup.find_all('th')),
            ('li', soup.find_all('li')),
        ]

        for tag_name, tags in selectors:
            for tag in tags:
                # Skip elements without text content
                text = tag.get_text(strip=True)
                if not text or len(text) < 2:
                    continue

                # Skip very long text blocks
                if len(text) > 300:
                    text = text[:300] + '...'

                # Generate selectors
                from scraper_preview import generate_xpath, generate_css_selector, generate_dom_path
                try:
                    xpath = generate_xpath(tree, tag)
                except Exception as e:
                    logger.warning("Failed to generate XPath", tag=str(tag)[:100], error=str(e))
                    xpath = f"//{tag_name}"

                css_selector = generate_css_selector(tag)
                dom_path = generate_dom_path(tag)

                element_id += 1
                elements.append({
                    'id': f'el-{element_id}',
                    'type': tag_name,
                    'text': text,
                    'xpath': xpath,
                    'css': css_selector,
                    'path': dom_path
                })

                # Limit to 100 elements
                if len(elements) >= 100:
                    break

            if len(elements) >= 100:
                break

        # Build response data
        response_data = {
            'url': url,
            'title': title,
            'elements': elements,
            'tier_info': {
                'tier_used': tier_used,
                'tier_name': TIER_INFO[tier_used]['name'],
                'cost_per_page': TIER_INFO[tier_used]['cost_per_page'],
                'escalation_log': escalation_log,
            }
        }

        logger.info("Async scrape completed", task_id=task_id, element_count=len(elements), tier_used=tier_used)

        # Send completion update via WebSocket
        if ws_domain:
            broadcast_to_user(ws_domain, ws_stage, user_id, {
                'type': 'scraper:complete',
                'task_id': task_id,
                'status': 'completed',
                'data': response_data
            })

    except Exception as e:
        logger.error("Async scrape failed", task_id=task_id, url=url, error=str(e))

        # Send error update via WebSocket
        if ws_domain:
            broadcast_to_user(ws_domain, ws_stage, user_id, {
                'type': 'scraper:error',
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            })


def invoke_scraper_async(
    user_id: str,
    url: str,
    task_id: str,
    min_tier: int = 1,
    max_tier: int = 4
):
    """
    Invoke the scraper worker Lambda asynchronously.

    Args:
        user_id: User who initiated the scrape
        url: URL to scrape
        task_id: Unique task identifier
        min_tier: Minimum tier to start with
        max_tier: Maximum tier to allow
    """
    function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'snowscrape-scraper-preview-async-worker')

    # Replace 'start' with 'worker' if present in function name
    if 'start' in function_name:
        function_name = function_name.replace('start', 'worker')
    elif function_name == 'snowscrape-scraper-preview':
        function_name = 'snowscrape-scraper-preview-async-worker'

    payload = {
        'task_id': task_id,
        'user_id': user_id,
        'url': url,
        'min_tier': min_tier,
        'max_tier': max_tier,
        'source': 'async_scraper'
    }

    try:
        # Invoke Lambda asynchronously (Event invocation type)
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(payload)
        )

        logger.info("Invoked scraper worker Lambda", task_id=task_id, function=function_name, status_code=response['StatusCode'])

    except Exception as e:
        logger.error("Failed to invoke scraper worker Lambda", task_id=task_id, error=str(e))
        raise


def start_async_scrape(user_id: str, url: str, min_tier: int = 1, max_tier: int = 4) -> Dict[str, Any]:
    """
    Start an async scrape operation and return immediately with task ID.
    Invokes worker Lambda asynchronously to do the actual scraping.

    Args:
        user_id: User who initiated the scrape
        url: URL to scrape
        min_tier: Minimum tier to start with
        max_tier: Maximum tier to allow

    Returns:
        Dictionary with task_id and initial status
    """
    task_id = str(uuid.uuid4())

    logger.info("Starting async scrape task", task_id=task_id, url=url, user_id=user_id)

    # Invoke worker Lambda asynchronously
    invoke_scraper_async(
        user_id=user_id,
        url=url,
        task_id=task_id,
        min_tier=min_tier,
        max_tier=max_tier
    )

    return {
        'task_id': task_id,
        'status': 'started',
        'url': url,
        'message': 'Scrape started. Connect to WebSocket and subscribe to channel for progress updates.',
        'websocket_channel': f'scraper:{task_id}',
        'websocket_url': f"wss://{os.environ.get('WS_API_DOMAIN')}/{os.environ.get('WS_API_STAGE', 'dev')}"
    }

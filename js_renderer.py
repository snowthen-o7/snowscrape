"""
JavaScript Renderer using Playwright
Renders JavaScript-heavy websites in headless Chromium browser
"""

import json
import os
import base64
from typing import Dict, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from logger import get_logger

logger = get_logger(__name__)


def render_page_with_playwright(url: str, render_config: Dict) -> Dict:
    """
    Render a page using Playwright headless browser.

    Args:
        url: URL to render
        render_config: Configuration dict with:
            - wait_strategy: 'load', 'domcontentloaded', 'networkidle' (default)
            - wait_timeout_ms: Timeout in milliseconds (default: 30000)
            - wait_for_selector: Optional CSS selector to wait for
            - viewport: Dict with width and height (default: 1920x1080)
            - capture_screenshot: Boolean to capture screenshot (default: False)
            - screenshot_full_page: Boolean for full page screenshot (default: False)
            - block_resources: List of resource types to block (e.g. ['image', 'stylesheet'])
            - user_agent: Optional custom user agent
            - proxy_url: Optional proxy URL

    Returns:
        Dict with status, content, and optional screenshot
    """
    try:
        logger.info("Starting Playwright render", url=url)

        # Extract configuration
        wait_strategy = render_config.get('wait_strategy', 'networkidle')
        wait_timeout = render_config.get('wait_timeout_ms', 30000)
        wait_for_selector = render_config.get('wait_for_selector')
        viewport = render_config.get('viewport', {'width': 1920, 'height': 1080})
        capture_screenshot = render_config.get('capture_screenshot', False)
        screenshot_full_page = render_config.get('screenshot_full_page', False)
        block_resources = render_config.get('block_resources', [])
        user_agent = render_config.get('user_agent')
        proxy_url = render_config.get('proxy_url')

        # Launch Playwright
        with sync_playwright() as playwright:
            # Browser launch options
            launch_options = {
                'headless': True,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-gpu'
                ]
            }

            # Add proxy if provided
            if proxy_url:
                # Parse proxy URL to extract components
                import re
                match = re.match(r'http://([^:]+):([^@]+)@([^:]+):(\d+)', proxy_url)
                if match:
                    username, password, server, port = match.groups()
                    launch_options['proxy'] = {
                        'server': f'http://{server}:{port}',
                        'username': username,
                        'password': password
                    }
                    logger.info("Using proxy for rendering", server=f'{server}:{port}')

            browser = playwright.chromium.launch(**launch_options)

            # Create context with viewport and user agent
            context_options = {
                'viewport': viewport,
                'ignore_https_errors': True
            }

            if user_agent:
                context_options['user_agent'] = user_agent

            context = browser.new_context(**context_options)

            # Block resources if specified
            if block_resources:
                def handle_route(route):
                    if route.request.resource_type in block_resources:
                        route.abort()
                    else:
                        route.continue_()

                context.route('**/*', handle_route)
                logger.info("Blocking resources", types=block_resources)

            page = context.new_page()

            # Set default timeout
            page.set_default_timeout(wait_timeout)

            # Navigate to URL
            logger.info("Navigating to URL", url=url, wait_strategy=wait_strategy)

            page.goto(url, wait_until=wait_strategy, timeout=wait_timeout)

            # Wait for specific selector if provided
            if wait_for_selector:
                logger.info("Waiting for selector", selector=wait_for_selector)
                page.wait_for_selector(wait_for_selector, timeout=wait_timeout)

            # Get rendered HTML content
            content = page.content()

            logger.info("Page rendered successfully", url=url, content_length=len(content))

            # Capture screenshot if requested
            screenshot_data = None
            if capture_screenshot:
                logger.info("Capturing screenshot", full_page=screenshot_full_page)
                screenshot_bytes = page.screenshot(full_page=screenshot_full_page)
                # Convert to base64 for easier transport
                screenshot_data = base64.b64encode(screenshot_bytes).decode('utf-8')
                logger.info("Screenshot captured", size_bytes=len(screenshot_bytes))

            # Close browser
            browser.close()

            return {
                'status': 'success',
                'content': content,
                'screenshot': screenshot_data,
                'url': url
            }

    except PlaywrightTimeoutError as e:
        logger.error("Playwright timeout", url=url, error=str(e))
        return {
            'status': 'error',
            'error': 'Timeout waiting for page to load',
            'error_type': 'timeout',
            'url': url
        }

    except Exception as e:
        logger.error("Playwright rendering failed", url=url, error=str(e))
        return {
            'status': 'error',
            'error': str(e),
            'error_type': 'render_error',
            'url': url
        }


def render_handler(event, context):
    """
    AWS Lambda handler for JavaScript rendering.

    Event structure:
    {
        "url": "https://example.com",
        "render_config": {
            "wait_strategy": "networkidle",
            "wait_timeout_ms": 30000,
            "capture_screenshot": false
        }
    }

    Returns:
    {
        "status": "success",
        "content": "<html>...</html>",
        "screenshot": "base64_string" (optional)
    }
    """
    try:
        # Extract parameters from event
        url = event.get('url')
        render_config = event.get('render_config', {})

        if not url:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'status': 'error',
                    'error': 'URL is required'
                })
            }

        logger.info("Received render request", url=url, config=render_config)

        # Render the page
        result = render_page_with_playwright(url, render_config)

        # Return result
        if result['status'] == 'success':
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps(result)
            }

    except Exception as e:
        logger.error("Lambda handler error", error=str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e),
                'error_type': 'handler_error'
            })
        }


# For local testing
if __name__ == '__main__':
    import sys

    test_event = {
        'url': sys.argv[1] if len(sys.argv) > 1 else 'https://example.com',
        'render_config': {
            'wait_strategy': 'networkidle',
            'wait_timeout_ms': 30000,
            'capture_screenshot': False
        }
    }

    result = render_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))

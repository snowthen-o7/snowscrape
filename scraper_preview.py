"""
Scraper Preview Module
Handles DOM parsing and selector testing for the visual scraper builder.
"""

import requests
from bs4 import BeautifulSoup
from lxml import html as lxml_html, etree
import re
from typing import List, Dict, Any, Optional
from logger import get_logger

logger = get_logger(__name__)

def fetch_and_parse_page(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Fetches a URL and returns a simplified DOM structure for visual selection.

    Args:
        url: The target URL to fetch and parse
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dictionary containing page title and list of selectable elements

    Raises:
        requests.RequestException: If the URL cannot be fetched
        Exception: For parsing errors
    """
    logger.info("Fetching URL for preview", url=url)

    # Fetch the page
    headers = {
        'User-Agent': 'SnowScrape Visual Builder/1.0 (+https://snowscrape.com)'
    }
    response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    response.raise_for_status()

    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Parse with lxml for better XPath support
    tree = lxml_html.fromstring(response.content)

    # Extract page title
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else url

    # Extract relevant elements
    elements = []
    element_id = 0

    # Target elements that typically contain data
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

            # Skip very long text blocks (likely not specific data points)
            if len(text) > 300:
                text = text[:300] + '...'

            # Generate XPath
            try:
                xpath = generate_xpath(tree, tag)
            except Exception as e:
                logger.warning("Failed to generate XPath", tag=str(tag)[:100], error=str(e))
                xpath = f"//{tag_name}"

            # Generate CSS selector
            css_selector = generate_css_selector(tag)

            # Generate DOM path
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

            # Limit to 100 elements to avoid overwhelming the UI
            if len(elements) >= 100:
                break

        if len(elements) >= 100:
            break

    logger.info("Page parsed successfully", url=url, element_count=len(elements))

    return {
        'url': url,
        'title': title,
        'elements': elements
    }


def generate_xpath(tree: lxml_html.HtmlElement, soup_tag: Any) -> str:
    """
    Generate an XPath for a BeautifulSoup tag using lxml.
    """
    # Try to find the element in the lxml tree by matching attributes and content
    tag_name = soup_tag.name
    text_content = soup_tag.get_text(strip=True)[:50]  # Use first 50 chars for matching

    # Build a basic XPath with class and id if available
    class_attr = soup_tag.get('class', [])
    id_attr = soup_tag.get('id')

    if id_attr:
        # If element has an ID, use it (most specific)
        xpath = f"//{tag_name}[@id='{id_attr}']"
    elif class_attr:
        # If element has classes, use them
        class_str = ' '.join(class_attr)
        xpath = f"//{tag_name}[contains(@class, '{class_attr[0]}')]"
    else:
        # Fallback to tag name with text matching (less reliable)
        xpath = f"//{tag_name}"

    return xpath


def generate_css_selector(tag: Any) -> str:
    """
    Generate a CSS selector for a BeautifulSoup tag.
    """
    tag_name = tag.name
    class_attr = tag.get('class', [])
    id_attr = tag.get('id')

    if id_attr:
        return f"#{id_attr}"
    elif class_attr:
        # Use the first class as the primary selector
        return f"{tag_name}.{class_attr[0]}"
    else:
        return tag_name


def generate_dom_path(tag: Any) -> str:
    """
    Generate a DOM path like "body > div.container > h1.title".
    """
    path_parts = []
    current = tag

    # Walk up the tree
    while current and current.name and current.name != '[document]':
        part = current.name

        # Add class or id if available
        class_attr = current.get('class', [])
        id_attr = current.get('id')

        if id_attr:
            part += f'#{id_attr}'
        elif class_attr:
            part += f'.{class_attr[0]}'

        path_parts.insert(0, part)
        current = current.parent

        # Limit depth to avoid overly long paths
        if len(path_parts) >= 6:
            break

    return ' > '.join(path_parts)


def test_extraction(url: str, selectors: List[Dict[str, str]], timeout: int = 10) -> List[Dict[str, Any]]:
    """
    Tests extraction with given selectors on a URL.

    Args:
        url: The target URL to scrape
        selectors: List of selector definitions with name, type, and selector
        timeout: Request timeout in seconds (default: 10)

    Returns:
        List containing extracted data as dictionaries

    Raises:
        requests.RequestException: If the URL cannot be fetched
        Exception: For extraction errors
    """
    logger.info("Testing extraction", url=url, selector_count=len(selectors))

    # Fetch the page
    headers = {
        'User-Agent': 'SnowScrape Visual Builder/1.0 (+https://snowscrape.com)'
    }
    response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    response.raise_for_status()

    # Parse with both BeautifulSoup and lxml
    soup = BeautifulSoup(response.content, 'html.parser')
    tree = lxml_html.fromstring(response.content)

    # Extract data using selectors
    result = {}

    for selector_def in selectors:
        name = selector_def['name']
        selector_type = selector_def['type']
        selector = selector_def['selector']

        try:
            if selector_type == 'xpath':
                # Use lxml for XPath
                elements = tree.xpath(selector)
                if elements:
                    # Get text from first match
                    if hasattr(elements[0], 'text_content'):
                        result[name] = elements[0].text_content().strip()
                    else:
                        result[name] = str(elements[0]).strip()
                else:
                    result[name] = None

            elif selector_type == 'css':
                # Use BeautifulSoup for CSS selectors
                elements = soup.select(selector)
                if elements:
                    result[name] = elements[0].get_text(strip=True)
                else:
                    result[name] = None

            elif selector_type == 'regex':
                # Apply regex to page content
                match = re.search(selector, response.text)
                if match:
                    # Return first capturing group, or full match if no groups
                    result[name] = match.group(1) if match.groups() else match.group(0)
                else:
                    result[name] = None
            else:
                logger.warning("Unknown selector type", selector_type=selector_type)
                result[name] = None

        except Exception as e:
            logger.error("Extraction failed for selector",
                        name=name,
                        selector_type=selector_type,
                        selector=selector,
                        error=str(e))
            result[name] = None

    logger.info("Extraction test completed", url=url, results_count=len(result))

    # Return as array with single result object
    return [result]

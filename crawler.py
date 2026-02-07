import json
import jsonpath_ng
import re
import requests
import time

from bs4 import BeautifulSoup
from lxml import etree
from logger import get_logger
from rate_limiter import DomainRateLimiter, DEFAULT_MIN_DELAY
from validators import validate_scrape_url, ValidationError as ScrapeValidationError

logger = get_logger(__name__)


def process_job(job_data):
    # Initialize per-domain rate limiter with optional crawl_delay from job config
    crawl_delay = job_data.get("crawl_delay", DEFAULT_MIN_DELAY)
    rate_limiter = DomainRateLimiter(min_delay=crawl_delay)

    urls = job_data["urls"]
    results = []
    for url in urls[:3] if job_data.get("test") else urls:
        rate_limiter.wait_if_needed(url)
        result = crawl_url(url, job_data["queries"])
        results.append(result)
    return results


def crawl_url(url, queries):
    result = {
        "url": url,
        "http_code": None,
        "error_info": None,
        "query_results": {},
        "removed": False,
        "ran": False,
    }
    try:
        # SSRF protection: validate URL before making any request
        try:
            validate_scrape_url(url)
        except ScrapeValidationError as e:
            result["error_info"] = f"URL validation failed (SSRF protection): {str(e)}"
            return result

        response = requests.get(url)
        result["http_code"] = response.status_code
        for query in queries:
            result["query_results"][query["name"]] = execute_query(response.text, query)
        result["ran"] = True
    except Exception as e:
        result["error_info"] = str(e)
    return result


def execute_query(content, query):
    """
    Execute a single query on the provided content.

    Args:
        content (str): The page content (HTML or JSON as string)
        query (dict): Query configuration with 'type', 'selector', and optional 'join'

    Returns:
        str or list or None: Extracted data based on query type and join flag
    """
    query_type = query.get("type")
    selector = query.get("selector") or query.get("query")
    join_flag = query.get("join", False)

    if not selector:
        return None

    try:
        results = []

        if query_type == "xpath":
            # Parse HTML and execute XPath query
            html_tree = etree.HTML(content.encode('utf-8') if isinstance(content, str) else content)
            xpath_results = html_tree.xpath(selector)
            results = [str(result) for result in xpath_results]

        elif query_type == "regex":
            # Execute regex pattern matching
            results = re.findall(selector, content)

        elif query_type == "jsonpath":
            # Parse JSON and execute JSONPath query
            try:
                json_data = json.loads(content) if isinstance(content, str) else content
                jsonpath_expr = jsonpath_ng.parse(selector)
                results = [match.value for match in jsonpath_expr.find(json_data)]
            except json.JSONDecodeError as e:
                logger.error("Error parsing JSON for JSONPath query", error=str(e))
                return None

        else:
            logger.warning("Unknown query type", query_type=query_type)
            return None

        # If join flag is set, concatenate results with pipe delimiter
        if join_flag and results:
            return '|'.join(str(r) for r in results)
        elif results:
            return results if len(results) > 1 else (results[0] if results else None)
        else:
            return None

    except Exception as e:
        logger.error("Error executing query", query_type=query_type, error=str(e))
        return None

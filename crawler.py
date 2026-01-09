import json
import jsonpath_ng
import re
import requests
import time

from bs4 import BeautifulSoup
from lxml import etree


def process_job(job_data):
    urls = job_data["urls"]
    results = []
    for url in urls[:3] if job_data.get("test") else urls:
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
                print(f"Error parsing JSON for JSONPath query: {str(e)}")
                return None

        else:
            print(f"Unknown query type: {query_type}")
            return None

        # If join flag is set, concatenate results with pipe delimiter
        if join_flag and results:
            return '|'.join(str(r) for r in results)
        elif results:
            return results if len(results) > 1 else (results[0] if results else None)
        else:
            return None

    except Exception as e:
        print(f"Error executing {query_type} query: {str(e)}")
        return None

import requests
import time


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
    if query["type"] == "xpath":
        # Implement XPath query logic
        pass
    elif query["type"] == "regex":
        # Implement Regex query logic
        pass
    elif query["type"] == "jsonpath":
        # Implement JSONPath query logic
        pass
    return None

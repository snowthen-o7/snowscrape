import boto3
import json
import jsonpath_ng
import os
import re
import signal

from bs4 import BeautifulSoup
from lxml import etree
from typing import Any, Dict, List, Optional

from logger import get_logger
from pdf_handler import is_pdf_content, process_pdf_query

logger = get_logger(__name__)


class RegexTimeoutError(Exception):
	"""Raised when a regex operation exceeds the allowed execution time."""
	pass


def _regex_timeout_handler(signum, frame):
	"""Signal handler for regex execution timeout."""
	raise RegexTimeoutError("Regex execution timed out after 5 seconds")


def safe_regex_findall(pattern: str, text: str, timeout_seconds: int = 5) -> List[str]:
	"""
	Execute re.findall() with a timeout to prevent catastrophic backtracking.

	Uses signal.alarm() on Linux/Lambda to enforce a 5-second timeout.

	Args:
		pattern: The regex pattern to search for.
		text: The text to search in.
		timeout_seconds: Maximum seconds allowed for execution.

	Returns:
		List of matches found.

	Raises:
		RegexTimeoutError: If regex execution exceeds timeout.
		re.error: If the regex pattern is invalid.
	"""
	old_handler = signal.signal(signal.SIGALRM, _regex_timeout_handler)
	signal.alarm(timeout_seconds)
	try:
		results = re.findall(pattern, text)
		signal.alarm(0)  # Cancel the alarm on success
		return results
	except RegexTimeoutError:
		raise RegexTimeoutError(
			f"Regex pattern execution timed out after {timeout_seconds} seconds. "
			"The pattern may cause catastrophic backtracking."
		)
	finally:
		signal.alarm(0)  # Ensure alarm is always cancelled
		signal.signal(signal.SIGALRM, old_handler)  # Restore previous handler

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'us-east-2'))
table = dynamodb.Table(os.environ['DYNAMODB_JOBS_TABLE'])

def get_crawl(job_id, crawl_id):
	"""
	Retrieve details of a specific URL crawl for a job.

	Args:
		job_id (str): The job ID
		crawl_id (str): The crawl ID (URL or URL hash)

	Returns:
		dict: Crawl details including URL, status, results, timestamps
		None: If crawl not found
	"""
	url_table = dynamodb.Table(os.environ['DYNAMODB_URLS_TABLE'])

	try:
		# Query the URL table for the specific crawl
		# crawl_id is assumed to be the URL or a URL identifier
		response = url_table.get_item(
			Key={
				'job_id': job_id,
				'url': crawl_id  # Assuming crawl_id is the URL
			}
		)

		item = response.get('Item')
		if item:
			return {
				'job_id': item.get('job_id'),
				'url': item.get('url'),
				'state': item.get('state', 'unknown'),
				'attempts': item.get('attempts', 0),
				'last_crawled': item.get('last_crawled'),
				'error': item.get('error'),
				'http_code': item.get('http_code'),
				'results': item.get('results', {})
			}
		else:
			logger.warning("Crawl not found", job_id=job_id, crawl_id=crawl_id)
			return None

	except Exception as e:
		logger.error("Error retrieving crawl details", error=str(e))
		return None

def process_queries(
	page_content: bytes,
	queries: List[Dict[str, Any]],
	content_type: Optional[str] = None
) -> Dict[str, Any]:
	"""
	Process the queries on the given page content and return the extracted data.

	Args:
	- page_content (bytes): The content of the page (HTML, JSON, or PDF).
	- queries (list): A list of queries to run on the page content.
	- content_type (str): Optional Content-Type header to help detect content format.

	Returns:
	- dict: A dictionary of extracted data for each query.
	"""
	extracted_data = {}

	# Check if content is PDF
	is_pdf = is_pdf_content(page_content, content_type)

	# Only parse as HTML if not PDF and we have non-PDF queries
	html_tree = None
	soup = None
	has_html_queries = any(q.get('type') in ['xpath', 'regex'] for q in queries)

	if not is_pdf and has_html_queries:
		try:
			soup = BeautifulSoup(page_content, 'html.parser')
			html_tree = etree.HTML(page_content)
		except Exception as e:
			logger.error("Error parsing HTML content", error=str(e))

	for query in queries:
		query_name = query.get('name', 'unnamed')
		query_type = query.get('type')
		query_expression = query.get('query')
		join_flag = query.get('join', False)

		# PDF query types don't require expression (can extract all text/tables)
		if not query_expression and query_type not in ['pdf_text', 'pdf_table', 'pdf_metadata']:
			continue

		try:
			results = []

			if query_type == 'xpath':
				if html_tree is None:
					logger.warning("Cannot run XPath on PDF content, use pdf_text or pdf_table instead")
					extracted_data[query_name] = None
					continue
				# Use XPath to extract data
				xpath_results = html_tree.xpath(query_expression)
				results = [str(result) for result in xpath_results]

			elif query_type == 'regex':
				# Use Regex to extract data with timeout protection
				# For PDFs, we should extract text first
				try:
					if is_pdf:
						from pdf_handler import extract_pdf_text
						text_content = extract_pdf_text(page_content)
						results = safe_regex_findall(query_expression, text_content)
					else:
						results = safe_regex_findall(query_expression, str(page_content))
				except RegexTimeoutError as e:
					logger.warning("Regex timeout for query", query_name=query_name, error=str(e))
					extracted_data[query_name] = None
					continue

			elif query_type == 'jsonpath':
				# Use JSONPath to extract data from JSON
				json_data = json.loads(page_content)
				jsonpath_expr = jsonpath_ng.parse(query_expression)
				results = [match.value for match in jsonpath_expr.find(json_data)]

			elif query_type in ['pdf_text', 'pdf_table', 'pdf_metadata']:
				# PDF query types
				if not is_pdf:
					logger.warning("Cannot run PDF query on non-PDF content")
					extracted_data[query_name] = None
					continue

				# Process PDF query
				result = process_pdf_query(page_content, query)
				extracted_data[query_name] = result
				continue  # Skip the join logic below, PDF handler handles it

			else:
				logger.warning("Unknown query type", query_type=query_type)
				extracted_data[query_name] = None
				continue

			# If join is True, concatenate the results with a pipe '|'
			if join_flag and results:
				extracted_data[query_name] = '|'.join(str(r) for r in results)
			else:
				extracted_data[query_name] = results

		except Exception as e:
			logger.error("Error processing query", query_name=query_name, error=str(e))
			extracted_data[query_name] = None

	return extracted_data

import boto3
import json
import jsonpath_ng
import os
import re

from bs4 import BeautifulSoup
from lxml import etree
from typing import Any, Dict, List, Optional

from pdf_handler import is_pdf_content, process_pdf_query

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
			print(f"Crawl not found for job_id: {job_id}, crawl_id: {crawl_id}")
			return None

	except Exception as e:
		print(f"Error retrieving crawl details: {str(e)}")
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
			print(f"Error parsing HTML content: {str(e)}")

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
					print(f"Cannot run XPath on PDF content. Use pdf_text or pdf_table instead.")
					extracted_data[query_name] = None
					continue
				# Use XPath to extract data
				xpath_results = html_tree.xpath(query_expression)
				results = [str(result) for result in xpath_results]

			elif query_type == 'regex':
				# Use Regex to extract data
				# For PDFs, we should extract text first
				if is_pdf:
					from pdf_handler import extract_pdf_text
					text_content = extract_pdf_text(page_content)
					results = re.findall(query_expression, text_content)
				else:
					results = re.findall(query_expression, str(page_content))

			elif query_type == 'jsonpath':
				# Use JSONPath to extract data from JSON
				json_data = json.loads(page_content)
				jsonpath_expr = jsonpath_ng.parse(query_expression)
				results = [match.value for match in jsonpath_expr.find(json_data)]

			elif query_type in ['pdf_text', 'pdf_table', 'pdf_metadata']:
				# PDF query types
				if not is_pdf:
					print(f"Cannot run PDF query on non-PDF content.")
					extracted_data[query_name] = None
					continue

				# Process PDF query
				result = process_pdf_query(page_content, query)
				extracted_data[query_name] = result
				continue  # Skip the join logic below, PDF handler handles it

			else:
				print(f"Unknown query type: {query_type}")
				extracted_data[query_name] = None
				continue

			# If join is True, concatenate the results with a pipe '|'
			if join_flag and results:
				extracted_data[query_name] = '|'.join(str(r) for r in results)
			else:
				extracted_data[query_name] = results

		except Exception as e:
			print(f"Error processing query {query_name}: {str(e)}")
			extracted_data[query_name] = None

	return extracted_data
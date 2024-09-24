import boto3
import jsonpath_ng
import os
import re

from bs4 import BeautifulSoup
from lxml import etree
from typing import Any, Dict, List

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'us-east-2'))
table = dynamodb.Table(os.environ['DYNAMODB_JOBS_TABLE'])

def get_crawl(job_id, crawl_id):
	# Logic to retrieve details of a specific crawl
	pass

def process_queries(page_content: bytes, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
	"""
	Process the queries on the given page content and return the extracted data.
	
	Args:
	- page_content (bytes): The HTML content of the page.
	- queries (list): A list of queries to run on the page content.
	
	Returns:
	- dict: A dictionary of extracted data for each query.
	"""
	extracted_data = {}

	# Parse the page content using lxml or BeautifulSoup
	soup = BeautifulSoup(page_content, 'html.parser')
	html_tree = etree.HTML(page_content)

	for query in queries:
		query_name = query.get('name', 'unnamed')
		query_type = query.get('type')
		query_expression = query.get('query')
		join_flag = query.get('join', False)

		if not query_expression:
			continue

		try:
			results = []

			if query_type == 'xpath':
				# Use XPath to extract data
				xpath_results = html_tree.xpath(query_expression)
				results = [str(result) for result in xpath_results]
			elif query_type == 'regex':
				# Use Regex to extract data
				results = re.findall(query_expression, str(page_content))
			elif query_type == 'jsonpath':
				# Use JSONPath to extract data from JSON
				json_data = json.loads(page_content)
				jsonpath_expr = jsonpath_ng.parse(query_expression)
				results = [match.value for match in jsonpath_expr.find(json_data)]
			else:
				print(f"Unknown query type: {query_type}")
				extracted_data[query_name] = None
				continue

			# If join is True, concatenate the results with a pipe '|'
			if join_flag and results:
					extracted_data[query_name] = '|'.join(results)
			else:
					extracted_data[query_name] = results

		except Exception as e:
			print(f"Error processing query {query_name}: {str(e)}")
			extracted_data[query_name] = None

	return extracted_data
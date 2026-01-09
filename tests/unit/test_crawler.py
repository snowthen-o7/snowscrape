import json
import pytest
from crawler import execute_query, crawl_url


class TestExecuteQuery:
	"""Unit tests for the execute_query function."""

	def test_xpath_query_single_result(self, sample_html_content):
		"""Test XPath query that returns a single result."""
		query = {
			'type': 'xpath',
			'selector': '//title/text()',
			'join': False
		}
		result = execute_query(sample_html_content, query)
		assert result == 'Test Page'

	def test_xpath_query_multiple_results(self, sample_html_content):
		"""Test XPath query that returns multiple results."""
		query = {
			'type': 'xpath',
			'selector': '//li/text()',
			'join': False
		}
		result = execute_query(sample_html_content, query)
		assert isinstance(result, list)
		assert len(result) == 3
		assert 'Feature 1' in result
		assert 'Feature 2' in result
		assert 'Feature 3' in result

	def test_xpath_query_with_join(self, sample_html_content):
		"""Test XPath query with join flag enabled."""
		query = {
			'type': 'xpath',
			'selector': '//li/text()',
			'join': True
		}
		result = execute_query(sample_html_content, query)
		assert result == 'Feature 1|Feature 2|Feature 3'

	def test_xpath_query_no_results(self, sample_html_content):
		"""Test XPath query that returns no results."""
		query = {
			'type': 'xpath',
			'selector': '//nonexistent/text()',
			'join': False
		}
		result = execute_query(sample_html_content, query)
		assert result is None

	def test_regex_query_single_match(self, sample_html_content):
		"""Test regex query that matches once."""
		query = {
			'type': 'regex',
			'selector': r'\$(\d+\.\d{2})',
			'join': False
		}
		result = execute_query(sample_html_content, query)
		assert result == '99.99'

	def test_regex_query_multiple_matches(self):
		"""Test regex query that matches multiple times."""
		content = 'Prices: $10.50, $20.75, $30.00'
		query = {
			'type': 'regex',
			'selector': r'\$(\d+\.\d{2})',
			'join': False
		}
		result = execute_query(content, query)
		assert isinstance(result, list)
		assert len(result) == 3
		assert '10.50' in result
		assert '20.75' in result
		assert '30.00' in result

	def test_regex_query_with_join(self):
		"""Test regex query with join flag enabled."""
		content = 'Prices: $10.50, $20.75, $30.00'
		query = {
			'type': 'regex',
			'selector': r'\$(\d+\.\d{2})',
			'join': True
		}
		result = execute_query(content, query)
		assert result == '10.50|20.75|30.00'

	def test_regex_query_no_matches(self, sample_html_content):
		"""Test regex query that doesn't match anything."""
		query = {
			'type': 'regex',
			'selector': r'NOMATCH\d+',
			'join': False
		}
		result = execute_query(sample_html_content, query)
		assert result is None

	def test_jsonpath_query_single_value(self, sample_json_content):
		"""Test JSONPath query that returns a single value."""
		query = {
			'type': 'jsonpath',
			'selector': '$.product.name',
			'join': False
		}
		result = execute_query(json.dumps(sample_json_content), query)
		assert result == 'Test Product'

	def test_jsonpath_query_nested_value(self, sample_json_content):
		"""Test JSONPath query for nested value."""
		query = {
			'type': 'jsonpath',
			'selector': '$.product.metadata.manufacturer',
			'join': False
		}
		result = execute_query(json.dumps(sample_json_content), query)
		assert result == 'Test Corp'

	def test_jsonpath_query_array(self, sample_json_content):
		"""Test JSONPath query that returns an array."""
		query = {
			'type': 'jsonpath',
			'selector': '$.product.features[*]',
			'join': False
		}
		result = execute_query(json.dumps(sample_json_content), query)
		assert isinstance(result, list)
		assert len(result) == 3
		assert 'Feature 1' in result

	def test_jsonpath_query_with_join(self, sample_json_content):
		"""Test JSONPath query with join flag enabled."""
		query = {
			'type': 'jsonpath',
			'selector': '$.product.features[*]',
			'join': True
		}
		result = execute_query(json.dumps(sample_json_content), query)
		assert result == 'Feature 1|Feature 2|Feature 3'

	def test_jsonpath_query_invalid_json(self):
		"""Test JSONPath query with invalid JSON content."""
		query = {
			'type': 'jsonpath',
			'selector': '$.product.name',
			'join': False
		}
		result = execute_query('invalid json', query)
		assert result is None

	def test_jsonpath_query_no_matches(self, sample_json_content):
		"""Test JSONPath query that doesn't match anything."""
		query = {
			'type': 'jsonpath',
			'selector': '$.nonexistent.field',
			'join': False
		}
		result = execute_query(json.dumps(sample_json_content), query)
		assert result is None

	def test_query_without_selector(self, sample_html_content):
		"""Test query without selector returns None."""
		query = {
			'type': 'xpath',
			'join': False
		}
		result = execute_query(sample_html_content, query)
		assert result is None

	def test_query_with_query_key_instead_of_selector(self, sample_html_content):
		"""Test that 'query' key is treated as fallback for 'selector'."""
		query = {
			'type': 'xpath',
			'query': '//title/text()',
			'join': False
		}
		result = execute_query(sample_html_content, query)
		assert result == 'Test Page'

	def test_unknown_query_type(self, sample_html_content):
		"""Test unknown query type returns None."""
		query = {
			'type': 'unknown_type',
			'selector': 'something',
			'join': False
		}
		result = execute_query(sample_html_content, query)
		assert result is None

	def test_xpath_with_bytes_content(self):
		"""Test XPath query with bytes content."""
		content = b'<html><title>Test</title></html>'
		query = {
			'type': 'xpath',
			'selector': '//title/text()',
			'join': False
		}
		result = execute_query(content, query)
		assert result == 'Test'

	def test_join_flag_default_false(self, sample_html_content):
		"""Test that join flag defaults to False."""
		query = {
			'type': 'xpath',
			'selector': '//li/text()'
		}
		result = execute_query(sample_html_content, query)
		assert isinstance(result, list)

	def test_join_converts_to_string(self, sample_json_content):
		"""Test that join converts non-string results to strings."""
		query = {
			'type': 'jsonpath',
			'selector': '$.product.price',
			'join': True
		}
		result = execute_query(json.dumps(sample_json_content), query)
		assert result == '99.99'
		assert isinstance(result, str)


class TestCrawlUrl:
	"""Unit tests for the crawl_url function."""

	@pytest.mark.slow
	def test_crawl_url_success(self, mocker):
		"""Test successful URL crawl."""
		# Mock requests.get
		mock_response = mocker.Mock()
		mock_response.status_code = 200
		mock_response.text = '<html><title>Test</title></html>'
		mocker.patch('crawler.requests.get', return_value=mock_response)

		queries = [{
			'name': 'title',
			'type': 'xpath',
			'selector': '//title/text()',
			'join': False
		}]

		result = crawl_url('https://example.com', queries)

		assert result['url'] == 'https://example.com'
		assert result['http_code'] == 200
		assert result['error_info'] is None
		assert result['ran'] is True
		assert 'title' in result['query_results']
		assert result['query_results']['title'] == 'Test'

	@pytest.mark.slow
	def test_crawl_url_http_error(self, mocker):
		"""Test URL crawl with HTTP error."""
		# Mock requests.get to raise an exception
		mocker.patch('crawler.requests.get', side_effect=Exception('Connection error'))

		queries = [{
			'name': 'title',
			'type': 'xpath',
			'selector': '//title/text()',
			'join': False
		}]

		result = crawl_url('https://example.com', queries)

		assert result['url'] == 'https://example.com'
		assert result['http_code'] is None
		assert result['error_info'] == 'Connection error'
		assert result['ran'] is False

	@pytest.mark.slow
	def test_crawl_url_multiple_queries(self, mocker):
		"""Test URL crawl with multiple queries."""
		mock_response = mocker.Mock()
		mock_response.status_code = 200
		mock_response.text = '<html><title>Test</title><div class="price">$99.99</div></html>'
		mocker.patch('crawler.requests.get', return_value=mock_response)

		queries = [
			{
				'name': 'title',
				'type': 'xpath',
				'selector': '//title/text()',
				'join': False
			},
			{
				'name': 'price',
				'type': 'regex',
				'selector': r'\$(\d+\.\d{2})',
				'join': False
			}
		]

		result = crawl_url('https://example.com', queries)

		assert result['ran'] is True
		assert 'title' in result['query_results']
		assert 'price' in result['query_results']
		assert result['query_results']['title'] == 'Test'
		assert result['query_results']['price'] == '99.99'

import json
import pytest
import responses
from unittest.mock import Mock, patch, MagicMock
from utils import (
	cron_to_seconds,
	decimal_to_float,
	detect_csv_settings,
	detect_url_column,
	extract_token_from_event,
	parse_links_from_file,
	validate_job_data,
	fetch_file_content
)
from decimal import Decimal


class TestCronToSeconds:
	"""Unit tests for cron_to_seconds function."""

	def test_every_hour(self):
		"""Test conversion of hourly cron expression."""
		result = cron_to_seconds("0 * * * *")
		assert result == 3600

	def test_every_day(self):
		"""Test conversion of daily cron expression."""
		result = cron_to_seconds("0 0 * * *")
		assert result == 86400

	def test_every_15_minutes(self):
		"""Test conversion of 15-minute interval."""
		result = cron_to_seconds("*/15 * * * *")
		assert result == 900

	def test_every_30_minutes(self):
		"""Test conversion of 30-minute interval."""
		result = cron_to_seconds("*/30 * * * *")
		assert result == 1800

	def test_every_2_hours(self):
		"""Test conversion of 2-hour interval."""
		result = cron_to_seconds("0 */2 * * *")
		assert result == 7200

	def test_specific_time_returns_daily(self):
		"""Test that specific time (e.g., 9:30 AM) returns daily interval."""
		result = cron_to_seconds("30 9 * * *")
		assert result == 86400

	def test_invalid_format_returns_none(self):
		"""Test that invalid cron format returns None."""
		result = cron_to_seconds("0 *")
		assert result is None

	def test_empty_string_returns_none(self):
		"""Test that empty string returns None."""
		result = cron_to_seconds("")
		assert result is None

	def test_none_input_returns_none(self):
		"""Test that None input returns None."""
		result = cron_to_seconds(None)
		assert result is None


class TestDecimalToFloat:
	"""Unit tests for decimal_to_float function."""

	def test_convert_single_decimal(self):
		"""Test conversion of single Decimal value."""
		result = decimal_to_float(Decimal('99.99'))
		assert result == 99.99
		assert isinstance(result, float)

	def test_convert_dict_with_decimals(self):
		"""Test conversion of dictionary containing Decimals."""
		input_dict = {
			'price': Decimal('99.99'),
			'quantity': Decimal('5'),
			'name': 'Product'
		}
		result = decimal_to_float(input_dict)
		assert result['price'] == 99.99
		assert result['quantity'] == 5.0
		assert result['name'] == 'Product'

	def test_convert_list_with_decimals(self):
		"""Test conversion of list containing Decimals."""
		input_list = [Decimal('1.5'), Decimal('2.5'), 'string', 10]
		result = decimal_to_float(input_list)
		assert result == [1.5, 2.5, 'string', 10]

	def test_convert_nested_structure(self):
		"""Test conversion of nested dictionaries and lists."""
		input_data = {
			'products': [
				{'price': Decimal('10.99'), 'quantity': Decimal('5')},
				{'price': Decimal('20.50'), 'quantity': Decimal('3')}
			],
			'total': Decimal('99.99')
		}
		result = decimal_to_float(input_data)
		assert result['products'][0]['price'] == 10.99
		assert result['products'][1]['quantity'] == 3.0
		assert result['total'] == 99.99

	def test_non_decimal_values_unchanged(self):
		"""Test that non-Decimal values remain unchanged."""
		assert decimal_to_float('string') == 'string'
		assert decimal_to_float(42) == 42
		assert decimal_to_float(None) is None


class TestDetectCSVSettings:
	"""Unit tests for detect_csv_settings function."""

	def test_detect_comma_delimiter(self):
		"""Test detection of comma-delimited CSV."""
		csv_content = "name,url,price\nProduct1,http://example.com,99.99\n"
		result = detect_csv_settings(csv_content)
		assert result['delimiter'] == ','
		assert result['enclosure'] == '"'
		assert 'name' in result['headers']
		assert 'url' in result['headers']

	def test_detect_semicolon_delimiter(self):
		"""Test detection of semicolon-delimited CSV."""
		csv_content = "name;url;price\nProduct1;http://example.com;99.99\n"
		result = detect_csv_settings(csv_content)
		assert result['delimiter'] == ';'

	def test_detect_tab_delimiter(self):
		"""Test detection of tab-delimited CSV."""
		csv_content = "name\turl\tprice\nProduct1\thttp://example.com\t99.99\n"
		result = detect_csv_settings(csv_content)
		assert result['delimiter'] == '\t'

	def test_detect_pipe_delimiter(self):
		"""Test detection of pipe-delimited CSV."""
		csv_content = "name|url|price\nProduct1|http://example.com|99.99\n"
		result = detect_csv_settings(csv_content)
		assert result['delimiter'] == '|'

	def test_detect_with_quotes(self):
		"""Test detection with quoted values."""
		csv_content = '"name","url","price"\n"Product 1","http://example.com","99.99"\n'
		result = detect_csv_settings(csv_content)
		assert result['delimiter'] == ','
		assert result['enclosure'] == '"'

	def test_fallback_on_error(self):
		"""Test that function returns defaults on detection error."""
		csv_content = "invalid content without clear structure"
		result = detect_csv_settings(csv_content)
		assert result['delimiter'] == ','
		assert result['enclosure'] == '"'
		assert result['escape'] == ''
		assert result['headers'] == []


class TestDetectUrlColumn:
	"""Unit tests for detect_url_column function."""

	def test_detect_url_column(self):
		"""Test detection of 'url' column."""
		headers = ['name', 'url', 'price']
		result = detect_url_column(headers)
		assert result == 1

	def test_detect_link_column(self):
		"""Test detection of 'link' column."""
		headers = ['name', 'link', 'price']
		result = detect_url_column(headers)
		assert result == 1

	def test_detect_case_insensitive(self):
		"""Test case-insensitive detection."""
		headers = ['name', 'URL', 'price']
		result = detect_url_column(headers)
		assert result == 1

	def test_detect_with_partial_match(self):
		"""Test detection with partial matches like 'product_url'."""
		headers = ['name', 'product_url', 'price']
		result = detect_url_column(headers)
		assert result == 1

	def test_no_match_returns_none(self):
		"""Test that no match returns None."""
		headers = ['name', 'price', 'description']
		result = detect_url_column(headers)
		assert result is None


class TestExtractTokenFromEvent:
	"""Unit tests for extract_token_from_event function."""

	def test_extract_valid_token(self):
		"""Test extraction of valid Bearer token."""
		event = {
			'headers': {
				'Authorization': 'Bearer test-token-123'
			}
		}
		result = extract_token_from_event(event)
		assert result == 'test-token-123'

	def test_extract_token_case_sensitive(self):
		"""Test that Authorization header is case-sensitive."""
		event = {
			'headers': {
				'authorization': 'Bearer test-token-123'
			}
		}
		result = extract_token_from_event(event)
		assert result is None

	def test_no_authorization_header(self):
		"""Test extraction when Authorization header is missing."""
		event = {'headers': {}}
		result = extract_token_from_event(event)
		assert result is None

	def test_no_bearer_prefix(self):
		"""Test extraction when Bearer prefix is missing."""
		event = {
			'headers': {
				'Authorization': 'test-token-123'
			}
		}
		result = extract_token_from_event(event)
		assert result is None

	def test_empty_token(self):
		"""Test extraction with empty token after Bearer."""
		event = {
			'headers': {
				'Authorization': 'Bearer '
			}
		}
		result = extract_token_from_event(event)
		assert result == ''


class TestValidateJobData:
	"""Unit tests for validate_job_data function."""

	def test_valid_job_data(self):
		"""Test validation of complete, valid job data."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {
				'delimiter': ',',
				'enclosure': '"',
				'escape': '\\',
				'url_column': 0
			},
			'queries': [
				{
					'name': 'title',
					'type': 'xpath',
					'query': '//title/text()'
				}
			]
		}
		# Should not raise an exception
		validate_job_data(job_data)

	def test_missing_name_raises_error(self):
		"""Test that missing name raises ValueError."""
		job_data = {
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="must have a valid 'name'"):
			validate_job_data(job_data)

	def test_invalid_name_type_raises_error(self):
		"""Test that non-string name raises ValueError."""
		job_data = {
			'name': 123,
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="must have a valid 'name'"):
			validate_job_data(job_data)

	def test_missing_rate_limit_raises_error(self):
		"""Test that missing rate_limit raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="must have a 'rate_limit'"):
			validate_job_data(job_data)

	def test_invalid_rate_limit_type_raises_error(self):
		"""Test that non-integer rate_limit raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': '5',
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="must have a 'rate_limit'"):
			validate_job_data(job_data)

	def test_rate_limit_out_of_range_raises_error(self):
		"""Test that rate_limit outside 1-8 range raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 10,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="must have a 'rate_limit'"):
			validate_job_data(job_data)

	def test_missing_source_raises_error(self):
		"""Test that missing source raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="must have a valid 'source'"):
			validate_job_data(job_data)

	def test_missing_file_mapping_raises_error(self):
		"""Test that missing file_mapping raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="must have a valid 'file_mapping'"):
			validate_job_data(job_data)

	def test_file_mapping_missing_delimiter(self):
		"""Test that file_mapping without delimiter raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="must contain 'delimiter'"):
			validate_job_data(job_data)

	def test_file_mapping_invalid_delimiter(self):
		"""Test that invalid delimiter raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ':', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="Invalid 'delimiter'"):
			validate_job_data(job_data)

	def test_file_mapping_invalid_enclosure(self):
		"""Test that invalid enclosure raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '`', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="Invalid 'enclosure'"):
			validate_job_data(job_data)

	def test_file_mapping_invalid_escape(self):
		"""Test that invalid escape raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '~', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="Invalid 'escape'"):
			validate_job_data(job_data)

	def test_missing_queries_raises_error(self):
		"""Test that missing queries raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0}
		}
		with pytest.raises(ValueError, match="must have a 'queries'"):
			validate_job_data(job_data)

	def test_query_missing_name(self):
		"""Test that query without name raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'type': 'xpath', 'query': '//title'}]
		}
		with pytest.raises(ValueError, match="must have a valid 'name'"):
			validate_job_data(job_data)

	def test_query_invalid_type(self):
		"""Test that query with invalid type raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'css', 'query': 'title'}]
		}
		with pytest.raises(ValueError, match="must have a valid 'type'"):
			validate_job_data(job_data)

	def test_query_missing_query_field(self):
		"""Test that query without query field raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath'}]
		}
		with pytest.raises(ValueError, match="must have a valid 'query'"):
			validate_job_data(job_data)

	def test_valid_scheduling(self):
		"""Test validation with valid scheduling."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}],
			'scheduling': {
				'hours': [9, 12, 15],
				'days': ['Monday', 'Wednesday', 'Friday']
			}
		}
		# Should not raise an exception
		validate_job_data(job_data)

	def test_scheduling_invalid_hour(self):
		"""Test that invalid hour in scheduling raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}],
			'scheduling': {
				'hours': [9, 25],
				'days': ['Monday']
			}
		}
		with pytest.raises(ValueError, match="'hours' must be integers"):
			validate_job_data(job_data)

	def test_scheduling_invalid_day(self):
		"""Test that invalid day in scheduling raises ValueError."""
		job_data = {
			'name': 'Test Job',
			'rate_limit': 5,
			'source': 'https://example.com/urls.csv',
			'file_mapping': {'delimiter': ',', 'enclosure': '"', 'escape': '\\', 'url_column': 0},
			'queries': [{'name': 'title', 'type': 'xpath', 'query': '//title'}],
			'scheduling': {
				'hours': [9],
				'days': ['InvalidDay']
			}
		}
		with pytest.raises(ValueError, match="'days' must be one of"):
			validate_job_data(job_data)


class TestFetchFileContent:
	"""Unit tests for fetch_file_content function."""

	@responses.activate
	def test_fetch_http_url(self):
		"""Test fetching file content from HTTP URL."""
		url = 'http://example.com/urls.csv'
		content = 'url\nhttp://test1.com\nhttp://test2.com'
		responses.add(responses.GET, url, body=content, status=200)

		result = fetch_file_content(url)
		assert result == content

	@responses.activate
	def test_fetch_https_url(self):
		"""Test fetching file content from HTTPS URL."""
		url = 'https://example.com/urls.csv'
		content = 'url\nhttp://test1.com\nhttp://test2.com'
		responses.add(responses.GET, url, body=content, status=200)

		result = fetch_file_content(url)
		assert result == content

	def test_fetch_sftp_url_missing_credentials(self):
		"""Test that SFTP URL without credentials raises exception."""
		url = 'sftp://example.com/path/to/file.csv'
		with pytest.raises(Exception, match="must contain a username and password"):
			fetch_file_content(url)

	def test_unsupported_url_scheme(self):
		"""Test that unsupported URL scheme raises exception."""
		url = 'ftp://example.com/file.csv'
		with pytest.raises(Exception, match="Unsupported URL scheme"):
			fetch_file_content(url)


class TestParseLinksFromFile:
	"""Unit tests for parse_links_from_file function."""

	@responses.activate
	def test_parse_simple_csv_with_integer_column(self):
		"""Test parsing simple CSV with integer column index."""
		url = 'http://example.com/urls.csv'
		content = 'name,url,price\nProduct1,http://test1.com,99.99\nProduct2,http://test2.com,89.99'
		responses.add(responses.GET, url, body=content, status=200)

		file_mapping = {
			'delimiter': ',',
			'enclosure': '"',
			'escape': '\\',
			'url_column': 1
		}

		result = parse_links_from_file(file_mapping, url)
		assert 'http://test1.com' in result
		assert 'http://test2.com' in result
		assert len(result) == 2

	@responses.activate
	def test_parse_csv_with_string_column_name(self):
		"""Test parsing CSV with string column name."""
		url = 'http://example.com/urls.csv'
		content = 'name,product_url,price\nProduct1,http://test1.com,99.99\nProduct2,http://test2.com,89.99'
		responses.add(responses.GET, url, body=content, status=200)

		file_mapping = {
			'delimiter': ',',
			'enclosure': '"',
			'escape': '\\',
			'url_column': 'product_url'
		}

		result = parse_links_from_file(file_mapping, url)
		assert 'http://test1.com' in result
		assert 'http://test2.com' in result

	@responses.activate
	def test_parse_csv_with_default_column_detection(self):
		"""Test parsing CSV with automatic URL column detection."""
		url = 'http://example.com/urls.csv'
		content = 'name,url,price\nProduct1,http://test1.com,99.99\nProduct2,http://test2.com,89.99'
		responses.add(responses.GET, url, body=content, status=200)

		file_mapping = {
			'delimiter': ',',
			'enclosure': '"',
			'escape': '\\',
			'url_column': 'default'
		}

		result = parse_links_from_file(file_mapping, url)
		assert 'http://test1.com' in result
		assert 'http://test2.com' in result

	@responses.activate
	def test_parse_csv_with_semicolon_delimiter(self):
		"""Test parsing CSV with semicolon delimiter."""
		url = 'http://example.com/urls.csv'
		content = 'name;url;price\nProduct1;http://test1.com;99.99\nProduct2;http://test2.com;89.99'
		responses.add(responses.GET, url, body=content, status=200)

		file_mapping = {
			'delimiter': ';',
			'enclosure': '"',
			'escape': '\\',
			'url_column': 1
		}

		result = parse_links_from_file(file_mapping, url)
		assert 'http://test1.com' in result
		assert 'http://test2.com' in result

	@responses.activate
	def test_parse_csv_skips_empty_values(self):
		"""Test that empty URL values are skipped."""
		url = 'http://example.com/urls.csv'
		content = 'name,url,price\nProduct1,http://test1.com,99.99\nProduct2,,89.99\nProduct3,http://test3.com,79.99'
		responses.add(responses.GET, url, body=content, status=200)

		file_mapping = {
			'delimiter': ',',
			'enclosure': '"',
			'escape': '\\',
			'url_column': 1
		}

		result = parse_links_from_file(file_mapping, url)
		assert 'http://test1.com' in result
		assert 'http://test3.com' in result
		assert len(result) == 2

	@responses.activate
	def test_parse_csv_with_quoted_values(self):
		"""Test parsing CSV with quoted values."""
		url = 'http://example.com/urls.csv'
		content = '"name","url","price"\n"Product 1","http://test1.com","99.99"\n"Product 2","http://test2.com","89.99"'
		responses.add(responses.GET, url, body=content, status=200)

		file_mapping = {
			'delimiter': ',',
			'enclosure': '"',
			'escape': '\\',
			'url_column': 1
		}

		result = parse_links_from_file(file_mapping, url)
		assert 'http://test1.com' in result
		assert 'http://test2.com' in result

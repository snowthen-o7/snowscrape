import re
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, urlunparse


class ValidationError(Exception):
	"""Custom exception for validation errors."""
	pass


class InputValidator:
	"""
	Comprehensive input validation and sanitization utility.
	Provides validation for URLs, queries, job data, and other inputs.
	"""

	# URL validation patterns
	URL_PATTERN = re.compile(
		r'^https?://'  # http:// or https://
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
		r'localhost|'  # localhost
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
		r'(?::\d+)?'  # optional port
		r'(?:/?|[/?]\S+)$', re.IGNORECASE)

	# Dangerous XPath patterns to block
	DANGEROUS_XPATH_PATTERNS = [
		r'document\(',
		r'unparsed-text\(',
		r'doc\(',
		r'collection\(',
		r'system-property\(',
	]

	# Maximum lengths for various inputs
	MAX_JOB_NAME_LENGTH = 200
	MAX_URL_LENGTH = 2048
	MAX_QUERY_NAME_LENGTH = 100
	MAX_QUERY_SELECTOR_LENGTH = 1000
	MAX_QUERIES_PER_JOB = 50
	MAX_URLS_PER_JOB = 10000

	@staticmethod
	def validate_url(url: str, allow_sftp: bool = True) -> str:
		"""
		Validate and normalize a URL.

		Args:
			url: URL to validate
			allow_sftp: Whether to allow SFTP URLs

		Returns:
			Normalized URL

		Raises:
			ValidationError: If URL is invalid
		"""
		if not url or not isinstance(url, str):
			raise ValidationError("URL must be a non-empty string")

		url = url.strip()

		if len(url) > InputValidator.MAX_URL_LENGTH:
			raise ValidationError(f"URL exceeds maximum length of {InputValidator.MAX_URL_LENGTH}")

		# Parse URL
		try:
			parsed = urlparse(url)
		except Exception as e:
			raise ValidationError(f"Invalid URL format: {str(e)}")

		# Validate scheme
		allowed_schemes = ['http', 'https']
		if allow_sftp:
			allowed_schemes.append('sftp')

		if parsed.scheme not in allowed_schemes:
			raise ValidationError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")

		# Validate hostname
		if not parsed.netloc:
			raise ValidationError("URL must have a valid hostname")

		# Check for localhost/private IPs in production (optional)
		hostname = parsed.netloc.split(':')[0]
		if hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
			# Could add environment check here to block in production
			pass

		# Normalize URL (remove fragments, ensure proper formatting)
		normalized = urlunparse((
			parsed.scheme,
			parsed.netloc,
			parsed.path or '/',
			parsed.params,
			parsed.query,
			''  # Remove fragment
		))

		return normalized

	@staticmethod
	def validate_url_list(urls: List[str], max_count: Optional[int] = None) -> List[str]:
		"""
		Validate a list of URLs.

		Args:
			urls: List of URLs to validate
			max_count: Maximum number of URLs allowed

		Returns:
			List of normalized URLs

		Raises:
			ValidationError: If validation fails
		"""
		if not isinstance(urls, list):
			raise ValidationError("URLs must be provided as a list")

		if not urls:
			raise ValidationError("URL list cannot be empty")

		max_count = max_count or InputValidator.MAX_URLS_PER_JOB
		if len(urls) > max_count:
			raise ValidationError(f"URL list exceeds maximum of {max_count} URLs")

		# Validate each URL
		validated_urls = []
		for i, url in enumerate(urls):
			try:
				validated_url = InputValidator.validate_url(url, allow_sftp=False)
				validated_urls.append(validated_url)
			except ValidationError as e:
				raise ValidationError(f"Invalid URL at index {i}: {str(e)}")

		# Check for duplicates
		if len(set(validated_urls)) != len(validated_urls):
			raise ValidationError("Duplicate URLs detected in list")

		return validated_urls

	@staticmethod
	def validate_xpath_query(xpath: str) -> str:
		"""
		Validate and sanitize an XPath query.

		Args:
			xpath: XPath query to validate

		Returns:
			Sanitized XPath query

		Raises:
			ValidationError: If query is invalid or dangerous
		"""
		if not xpath or not isinstance(xpath, str):
			raise ValidationError("XPath query must be a non-empty string")

		xpath = xpath.strip()

		if len(xpath) > InputValidator.MAX_QUERY_SELECTOR_LENGTH:
			raise ValidationError(f"XPath query exceeds maximum length of {InputValidator.MAX_QUERY_SELECTOR_LENGTH}")

		# Check for dangerous patterns
		for pattern in InputValidator.DANGEROUS_XPATH_PATTERNS:
			if re.search(pattern, xpath, re.IGNORECASE):
				raise ValidationError(f"XPath query contains potentially dangerous function: {pattern}")

		# Basic XPath syntax validation (check for balanced brackets)
		if xpath.count('[') != xpath.count(']'):
			raise ValidationError("XPath query has unbalanced brackets")

		if xpath.count('(') != xpath.count(')'):
			raise ValidationError("XPath query has unbalanced parentheses")

		return xpath

	@staticmethod
	def validate_regex_pattern(pattern: str) -> str:
		"""
		Validate a regex pattern.

		Args:
			pattern: Regex pattern to validate

		Returns:
			Validated pattern

		Raises:
			ValidationError: If pattern is invalid
		"""
		if not pattern or not isinstance(pattern, str):
			raise ValidationError("Regex pattern must be a non-empty string")

		pattern = pattern.strip()

		if len(pattern) > InputValidator.MAX_QUERY_SELECTOR_LENGTH:
			raise ValidationError(f"Regex pattern exceeds maximum length of {InputValidator.MAX_QUERY_SELECTOR_LENGTH}")

		# Try to compile the pattern to check validity
		try:
			re.compile(pattern)
		except re.error as e:
			raise ValidationError(f"Invalid regex pattern: {str(e)}")

		# Check for catastrophic backtracking patterns (basic check)
		# Look for nested quantifiers like (a+)+ or (a*)*
		nested_quantifier_pattern = r'\([^)]*[*+]\)[*+]'
		if re.search(nested_quantifier_pattern, pattern):
			raise ValidationError("Regex pattern may cause catastrophic backtracking")

		return pattern

	@staticmethod
	def validate_jsonpath_query(jsonpath: str) -> str:
		"""
		Validate a JSONPath query.

		Args:
			jsonpath: JSONPath query to validate

		Returns:
			Validated query

		Raises:
			ValidationError: If query is invalid
		"""
		if not jsonpath or not isinstance(jsonpath, str):
			raise ValidationError("JSONPath query must be a non-empty string")

		jsonpath = jsonpath.strip()

		if len(jsonpath) > InputValidator.MAX_QUERY_SELECTOR_LENGTH:
			raise ValidationError(f"JSONPath query exceeds maximum length of {InputValidator.MAX_QUERY_SELECTOR_LENGTH}")

		# JSONPath must start with $ or @
		if not jsonpath.startswith(('$', '@')):
			raise ValidationError("JSONPath query must start with '$' or '@'")

		# Check for balanced brackets
		if jsonpath.count('[') != jsonpath.count(']'):
			raise ValidationError("JSONPath query has unbalanced brackets")

		return jsonpath

	@staticmethod
	def validate_query(query: Dict[str, Any]) -> Dict[str, Any]:
		"""
		Validate a query object.

		Args:
			query: Query dictionary to validate

		Returns:
			Validated query dictionary

		Raises:
			ValidationError: If query is invalid
		"""
		if not isinstance(query, dict):
			raise ValidationError("Query must be a dictionary")

		# Validate required fields
		if 'name' not in query:
			raise ValidationError("Query must have a 'name' field")

		if 'type' not in query:
			raise ValidationError("Query must have a 'type' field")

		# Validate name
		name = query['name']
		if not isinstance(name, str) or not name.strip():
			raise ValidationError("Query name must be a non-empty string")

		if len(name) > InputValidator.MAX_QUERY_NAME_LENGTH:
			raise ValidationError(f"Query name exceeds maximum length of {InputValidator.MAX_QUERY_NAME_LENGTH}")

		# Sanitize name (alphanumeric, underscore, hyphen only)
		if not re.match(r'^[a-zA-Z0-9_-]+$', name):
			raise ValidationError("Query name can only contain letters, numbers, underscores, and hyphens")

		# Validate type
		query_type = query['type']
		valid_types = ['xpath', 'regex', 'jsonpath']
		if query_type not in valid_types:
			raise ValidationError(f"Query type must be one of: {', '.join(valid_types)}")

		# Validate selector/query field
		selector = query.get('selector') or query.get('query')
		if not selector:
			raise ValidationError("Query must have a 'selector' or 'query' field")

		# Validate selector based on type
		if query_type == 'xpath':
			validated_selector = InputValidator.validate_xpath_query(selector)
		elif query_type == 'regex':
			validated_selector = InputValidator.validate_regex_pattern(selector)
		elif query_type == 'jsonpath':
			validated_selector = InputValidator.validate_jsonpath_query(selector)

		# Validate join flag
		join = query.get('join', False)
		if not isinstance(join, bool):
			raise ValidationError("Query 'join' flag must be a boolean")

		# Return validated query
		return {
			'name': name.strip(),
			'type': query_type,
			'selector': validated_selector,
			'join': join
		}

	@staticmethod
	def validate_queries(queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
		"""
		Validate a list of queries.

		Args:
			queries: List of query dictionaries

		Returns:
			List of validated queries

		Raises:
			ValidationError: If validation fails
		"""
		if not isinstance(queries, list):
			raise ValidationError("Queries must be provided as a list")

		if not queries:
			raise ValidationError("At least one query is required")

		if len(queries) > InputValidator.MAX_QUERIES_PER_JOB:
			raise ValidationError(f"Maximum of {InputValidator.MAX_QUERIES_PER_JOB} queries allowed per job")

		validated_queries = []
		query_names = set()

		for i, query in enumerate(queries):
			try:
				validated_query = InputValidator.validate_query(query)
				validated_queries.append(validated_query)

				# Check for duplicate names
				if validated_query['name'] in query_names:
					raise ValidationError(f"Duplicate query name: {validated_query['name']}")
				query_names.add(validated_query['name'])

			except ValidationError as e:
				raise ValidationError(f"Invalid query at index {i}: {str(e)}")

		return validated_queries

	@staticmethod
	def validate_file_mapping(file_mapping: Dict[str, Any]) -> Dict[str, Any]:
		"""
		Validate file mapping configuration.

		Args:
			file_mapping: File mapping dictionary

		Returns:
			Validated file mapping

		Raises:
			ValidationError: If validation fails
		"""
		if not isinstance(file_mapping, dict):
			raise ValidationError("File mapping must be a dictionary")

		required_keys = ['delimiter', 'enclosure', 'escape', 'url_column']
		for key in required_keys:
			if key not in file_mapping:
				raise ValidationError(f"File mapping must contain '{key}'")

		# Validate delimiter
		valid_delimiters = [',', ';', '|', '\t', '\\t']
		if file_mapping['delimiter'] not in valid_delimiters:
			raise ValidationError(f"Invalid delimiter. Must be one of: {', '.join(valid_delimiters)}")

		# Validate enclosure
		valid_enclosures = ['"', "'", 'none']
		if file_mapping['enclosure'] not in valid_enclosures:
			raise ValidationError(f"Invalid enclosure. Must be one of: {', '.join(valid_enclosures)}")

		# Validate escape
		valid_escapes = ['\\', '/', '"', "'", 'none']
		if file_mapping['escape'] not in valid_escapes:
			raise ValidationError(f"Invalid escape. Must be one of: {', '.join(valid_escapes)}")

		# Validate url_column
		url_column = file_mapping['url_column']
		if isinstance(url_column, int):
			if url_column < 0 or url_column > 100:
				raise ValidationError("URL column index must be between 0 and 100")
		elif isinstance(url_column, str):
			if url_column != 'default' and not re.match(r'^[a-zA-Z0-9_-]+$', url_column):
				raise ValidationError("URL column name can only contain letters, numbers, underscores, and hyphens")
		else:
			raise ValidationError("URL column must be an integer index or string name")

		return file_mapping

	@staticmethod
	def validate_rate_limit(rate_limit: Any) -> int:
		"""
		Validate rate limit value.

		Args:
			rate_limit: Rate limit value to validate

		Returns:
			Validated rate limit

		Raises:
			ValidationError: If validation fails
		"""
		if not isinstance(rate_limit, int):
			raise ValidationError("Rate limit must be an integer")

		if rate_limit < 1 or rate_limit > 8:
			raise ValidationError("Rate limit must be between 1 and 8")

		return rate_limit

	@staticmethod
	def validate_job_name(name: str) -> str:
		"""
		Validate and sanitize job name.

		Args:
			name: Job name to validate

		Returns:
			Sanitized job name

		Raises:
			ValidationError: If validation fails
		"""
		if not name or not isinstance(name, str):
			raise ValidationError("Job name must be a non-empty string")

		name = name.strip()

		if not name:
			raise ValidationError("Job name cannot be empty or whitespace only")

		if len(name) > InputValidator.MAX_JOB_NAME_LENGTH:
			raise ValidationError(f"Job name exceeds maximum length of {InputValidator.MAX_JOB_NAME_LENGTH}")

		# Remove control characters and normalize whitespace
		name = ' '.join(name.split())
		name = ''.join(char for char in name if ord(char) >= 32)

		return name

	@staticmethod
	def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
		"""
		Sanitize a string value by removing control characters and trimming.

		Args:
			value: String to sanitize
			max_length: Maximum allowed length

		Returns:
			Sanitized string

		Raises:
			ValidationError: If validation fails
		"""
		if not isinstance(value, str):
			raise ValidationError("Value must be a string")

		# Remove control characters (except newlines and tabs)
		value = ''.join(char for char in value if ord(char) >= 32 or char in ['\n', '\t'])

		# Trim whitespace
		value = value.strip()

		if max_length and len(value) > max_length:
			raise ValidationError(f"String exceeds maximum length of {max_length}")

		return value


# Convenience functions for common validations

def validate_job_data_strict(job_data: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Strictly validate and sanitize job data with comprehensive checks.

	Args:
		job_data: Job data dictionary to validate

	Returns:
		Validated and sanitized job data

	Raises:
		ValidationError: If validation fails
	"""
	validator = InputValidator()

	validated = {}

	# Validate name
	if 'name' not in job_data:
		raise ValidationError("Job must have a 'name' field")
	validated['name'] = validator.validate_job_name(job_data['name'])

	# Validate source URL
	if 'source' not in job_data:
		raise ValidationError("Job must have a 'source' field")
	validated['source'] = validator.validate_url(job_data['source'], allow_sftp=True)

	# Validate file mapping
	if 'file_mapping' not in job_data:
		raise ValidationError("Job must have a 'file_mapping' field")
	validated['file_mapping'] = validator.validate_file_mapping(job_data['file_mapping'])

	# Validate queries
	if 'queries' not in job_data:
		raise ValidationError("Job must have a 'queries' field")
	validated['queries'] = validator.validate_queries(job_data['queries'])

	# Validate rate limit
	if 'rate_limit' not in job_data:
		raise ValidationError("Job must have a 'rate_limit' field")
	validated['rate_limit'] = validator.validate_rate_limit(job_data['rate_limit'])

	# Validate scheduling (optional)
	if 'scheduling' in job_data and job_data['scheduling'] is not None:
		validated['scheduling'] = job_data['scheduling']  # Already validated by validate_job_data

	# Copy user_id if present (added by authentication)
	if 'user_id' in job_data:
		validated['user_id'] = job_data['user_id']

	# Copy job_id if present
	if 'job_id' in job_data:
		validated['job_id'] = job_data['job_id']

	return validated

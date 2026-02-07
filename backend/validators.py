import ipaddress
import re
import json
import socket
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse, urlunparse
from url_variable_resolver import URLVariableResolver


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

	# Whitelist of safe XPath functions
	ALLOWED_XPATH_FUNCTIONS = {
		# Text functions
		'text', 'contains', 'starts-with', 'ends-with', 'normalize-space',
		# Positional functions
		'position', 'last', 'count', 'string-length',
		# String manipulation functions
		'concat', 'substring', 'substring-before', 'substring-after',
		# Boolean functions
		'not', 'and', 'or', 'true', 'false',
		# Type conversion functions
		'string', 'number', 'boolean', 'translate', 'sum',
		# Node functions
		'local-name', 'name', 'namespace-uri',
		# Node type tests
		'comment', 'processing-instruction', 'node',
	}

	# Maximum lengths for various inputs
	MAX_JOB_NAME_LENGTH = 200
	MAX_URL_LENGTH = 2048
	MAX_QUERY_NAME_LENGTH = 100
	MAX_QUERY_SELECTOR_LENGTH = 1000
	MAX_QUERIES_PER_JOB = 50
	MAX_URLS_PER_JOB = 10000
	MAX_XPATH_LENGTH = 1000
	MAX_REGEX_PATTERN_LENGTH = 500
	MAX_REGEX_QUANTIFIERS = 5

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
		Validate and sanitize an XPath query using a function whitelist approach.

		Only allows known-safe XPath functions. Any function call not in the
		ALLOWED_XPATH_FUNCTIONS whitelist will be rejected.

		Args:
			xpath: XPath query to validate

		Returns:
			Sanitized XPath query

		Raises:
			ValidationError: If query is invalid or contains disallowed functions
		"""
		if not xpath or not isinstance(xpath, str):
			raise ValidationError("XPath query must be a non-empty string")

		xpath = xpath.strip()

		# Check max expression length
		if len(xpath) > InputValidator.MAX_XPATH_LENGTH:
			raise ValidationError(f"XPath query exceeds maximum length of {InputValidator.MAX_XPATH_LENGTH}")

		# Extract all function calls from the XPath expression
		# Matches word characters (including hyphens) followed by an opening parenthesis
		function_call_pattern = re.compile(r'(\w[\w-]*)\s*\(')
		found_functions = function_call_pattern.findall(xpath)

		# Check each function call against the whitelist
		for func_name in found_functions:
			if func_name not in InputValidator.ALLOWED_XPATH_FUNCTIONS:
				raise ValidationError(
					f"XPath function '{func_name}' is not allowed. "
					f"Only the following functions are permitted: "
					f"{', '.join(sorted(InputValidator.ALLOWED_XPATH_FUNCTIONS))}"
				)

		# Basic XPath syntax validation (check for balanced brackets)
		if xpath.count('[') != xpath.count(']'):
			raise ValidationError("XPath query has unbalanced brackets")

		if xpath.count('(') != xpath.count(')'):
			raise ValidationError("XPath query has unbalanced parentheses")

		# Check for excessive nesting depth
		max_depth = 0
		current_depth = 0
		for char in xpath:
			if char in ('[', '('):
				current_depth += 1
				max_depth = max(max_depth, current_depth)
			elif char in (']', ')'):
				current_depth -= 1
		if max_depth > 20:
			raise ValidationError("XPath query has excessive nesting depth (max 20 levels)")

		return xpath

	@staticmethod
	def validate_regex_pattern(pattern: str) -> str:
		"""
		Validate a regex pattern with enhanced ReDoS detection.

		Checks for:
		- Pattern length limit (500 characters)
		- Valid regex syntax
		- Nested quantifiers (e.g., (a+)+, (a*)*)
		- Alternation with overlapping patterns (e.g., (a|a), (a|ab))
		- Quantified groups with quantified alternation
		- Excessive quantifier count (max 5)

		Args:
			pattern: Regex pattern to validate

		Returns:
			Validated pattern

		Raises:
			ValidationError: If pattern is invalid or potentially dangerous
		"""
		if not pattern or not isinstance(pattern, str):
			raise ValidationError("Regex pattern must be a non-empty string")

		pattern = pattern.strip()

		# Enforce max pattern length of 500 characters
		if len(pattern) > InputValidator.MAX_REGEX_PATTERN_LENGTH:
			raise ValidationError(
				f"Regex pattern exceeds maximum length of "
				f"{InputValidator.MAX_REGEX_PATTERN_LENGTH} characters"
			)

		# Try to compile the pattern to check validity
		try:
			re.compile(pattern)
		except re.error as e:
			raise ValidationError(f"Invalid regex pattern: {str(e)}")

		# Check for catastrophic backtracking patterns

		# 1. Nested quantifiers like (a+)+ or (a*)*
		nested_quantifier_pattern = r'\([^)]*[*+]\)[*+]'
		if re.search(nested_quantifier_pattern, pattern):
			raise ValidationError(
				"Regex pattern may cause catastrophic backtracking "
				"(nested quantifiers detected)"
			)

		# 2. Alternation with overlapping patterns like (a|a) or (a|ab)
		# Extract groups with alternation and check for prefix overlap
		alternation_groups = re.findall(r'\(([^()]*\|[^()]*)\)', pattern)
		for group in alternation_groups:
			alternatives = group.split('|')
			# Check if any alternative is a prefix of another (overlapping)
			for i, alt_a in enumerate(alternatives):
				for j, alt_b in enumerate(alternatives):
					if i != j and alt_a and alt_b:
						# Strip quantifiers for comparison
						clean_a = re.sub(r'[*+?{}\[\]]', '', alt_a).strip()
						clean_b = re.sub(r'[*+?{}\[\]]', '', alt_b).strip()
						if clean_a and clean_b and (
							clean_a.startswith(clean_b) or clean_b.startswith(clean_a)
						):
							raise ValidationError(
								"Regex pattern may cause catastrophic backtracking "
								"(alternation with overlapping patterns detected)"
							)

		# 3. Quantified groups containing quantified alternation, e.g., (a+|b+)+
		quantified_alternation_pattern = r'\([^)]*[*+][^)]*\|[^)]*\)[*+]'
		if re.search(quantified_alternation_pattern, pattern):
			raise ValidationError(
				"Regex pattern may cause catastrophic backtracking "
				"(quantified group with quantified alternation detected)"
			)

		# 4. Max pattern complexity check: count quantifiers (* + ? {n} {n,m})
		quantifier_count = len(re.findall(r'(?<!\\)[*+?]|\{[\d,]+\}', pattern))
		if quantifier_count > InputValidator.MAX_REGEX_QUANTIFIERS:
			raise ValidationError(
				f"Regex pattern is too complex ({quantifier_count} quantifiers "
				f"detected, maximum is {InputValidator.MAX_REGEX_QUANTIFIERS})"
			)

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
		valid_types = ['xpath', 'regex', 'jsonpath', 'pdf_text', 'pdf_table', 'pdf_metadata']
		if query_type not in valid_types:
			raise ValidationError(f"Query type must be one of: {', '.join(valid_types)}")

		# PDF query types don't require a selector/expression
		pdf_types = ['pdf_text', 'pdf_table', 'pdf_metadata']

		# Validate selector/query field
		selector = query.get('selector') or query.get('query') or ''

		# Non-PDF queries require a selector
		if query_type not in pdf_types and not selector:
			raise ValidationError("Query must have a 'selector' or 'query' field")

		# Validate selector based on type
		validated_selector = selector  # Default to as-is for PDF types
		if query_type == 'xpath':
			validated_selector = InputValidator.validate_xpath_query(selector)
		elif query_type == 'regex':
			validated_selector = InputValidator.validate_regex_pattern(selector)
		elif query_type == 'jsonpath':
			validated_selector = InputValidator.validate_jsonpath_query(selector)
		elif query_type in pdf_types:
			# PDF queries can have an optional regex pattern (for pdf_text) or column name (for pdf_table)
			# No special validation needed, just pass through
			validated_selector = selector.strip() if selector else ''

		# Validate join flag
		join = query.get('join', False)
		if not isinstance(join, bool):
			raise ValidationError("Query 'join' flag must be a boolean")

		# Build validated query
		validated_query = {
			'name': name.strip(),
			'type': query_type,
			'selector': validated_selector,
			'join': join
		}

		# Include pdf_config for PDF queries if present
		if query_type in pdf_types and 'pdf_config' in query:
			pdf_config = query['pdf_config']
			if isinstance(pdf_config, dict):
				validated_query['pdf_config'] = pdf_config

		return validated_query

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

	@staticmethod
	def validate_url_template(url_template: str) -> str:
		"""
		Validate a URL template with optional date/time variables.

		URL templates can contain PHP-style date format variables like:
		- {{date}} -> default Y-m-d format
		- {{date:Y-m-d}} -> specific format
		- {{date+1d:Y-m-d}} -> with offset
		- {{time:H_i}} -> time variable

		Args:
			url_template: URL template to validate

		Returns:
			Validated URL template

		Raises:
			ValidationError: If template is invalid
		"""
		if not url_template or not isinstance(url_template, str):
			raise ValidationError("URL template must be a non-empty string")

		url_template = url_template.strip()

		if len(url_template) > InputValidator.MAX_URL_LENGTH:
			raise ValidationError(f"URL template exceeds maximum length of {InputValidator.MAX_URL_LENGTH}")

		# Use URLVariableResolver to validate the template
		is_valid, error = URLVariableResolver.validate_template(url_template)
		if not is_valid:
			raise ValidationError(f"Invalid URL template: {error}")

		# Resolve the template to validate that the base URL is valid
		resolved_url = URLVariableResolver.resolve(url_template)

		# Parse and validate the resolved URL
		try:
			parsed = urlparse(resolved_url)
		except Exception as e:
			raise ValidationError(f"Invalid resolved URL format: {str(e)}")

		# Validate scheme
		allowed_schemes = ['http', 'https']
		if parsed.scheme not in allowed_schemes:
			raise ValidationError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")

		# Validate hostname
		if not parsed.netloc:
			raise ValidationError("URL must have a valid hostname")

		return url_template

	@staticmethod
	def validate_source_type(source_type: str) -> str:
		"""
		Validate source type for job configuration.

		Args:
			source_type: Source type to validate ('csv' or 'direct_url')

		Returns:
			Validated source type

		Raises:
			ValidationError: If source type is invalid
		"""
		valid_types = ['csv', 'direct_url']
		if source_type not in valid_types:
			raise ValidationError(f"Source type must be one of: {', '.join(valid_types)}")
		return source_type

	@staticmethod
	def validate_timezone(tz: str) -> str:
		"""
		Validate a timezone string.

		Args:
			tz: Timezone name to validate (e.g., 'America/New_York')

		Returns:
			Validated timezone string

		Raises:
			ValidationError: If timezone is invalid
		"""
		if not tz:
			return 'UTC'  # Default to UTC

		is_valid, error = URLVariableResolver.validate_timezone(tz)
		if not is_valid:
			raise ValidationError(error)
		return tz


# ---- SSRF Protection ----

# IPv4 networks that must be blocked to prevent SSRF attacks
_BLOCKED_IPV4_NETWORKS = [
	ipaddress.IPv4Network('127.0.0.0/8'),       # Loopback
	ipaddress.IPv4Network('10.0.0.0/8'),         # Private (Class A)
	ipaddress.IPv4Network('172.16.0.0/12'),      # Private (Class B)
	ipaddress.IPv4Network('192.168.0.0/16'),     # Private (Class C)
	ipaddress.IPv4Network('169.254.0.0/16'),     # Link-local (includes AWS metadata 169.254.169.254)
	ipaddress.IPv4Network('0.0.0.0/8'),          # Unspecified / "this" network
]

# IPv6 networks that must be blocked to prevent SSRF attacks
_BLOCKED_IPV6_NETWORKS = [
	ipaddress.IPv6Network('::1/128'),            # Loopback
	ipaddress.IPv6Network('fc00::/7'),           # Unique local addresses
	ipaddress.IPv6Network('fe80::/10'),          # Link-local
]


def _is_ip_blocked(ip_str: str) -> bool:
	"""
	Check whether an IP address falls within any blocked range.

	Args:
		ip_str: IP address string (IPv4 or IPv6)

	Returns:
		True if the IP is in a blocked range, False otherwise.
	"""
	try:
		addr = ipaddress.ip_address(ip_str)
	except ValueError:
		# If the string is not a valid IP address, treat it as blocked
		# (fail-safe: deny rather than allow)
		return True

	if isinstance(addr, ipaddress.IPv4Address):
		return any(addr in network for network in _BLOCKED_IPV4_NETWORKS)
	elif isinstance(addr, ipaddress.IPv6Address):
		# Also check IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1)
		mapped_v4 = addr.ipv4_mapped
		if mapped_v4 is not None:
			return any(mapped_v4 in network for network in _BLOCKED_IPV4_NETWORKS)
		return any(addr in network for network in _BLOCKED_IPV6_NETWORKS)

	return True  # Unknown address type -- fail-safe deny


def validate_scrape_url(url: str) -> str:
	"""
	Validate a URL to prevent Server-Side Request Forgery (SSRF).

	Ensures the URL does not resolve to any private, loopback, or link-local
	IP address, blocking access to internal services such as the AWS metadata
	endpoint (169.254.169.254).

	Args:
		url: The URL to validate.

	Returns:
		The validated URL (stripped of whitespace).

	Raises:
		ValidationError: If the URL targets a blocked IP range, uses a
			disallowed scheme, or cannot be resolved.
	"""
	if not url or not isinstance(url, str):
		raise ValidationError("URL must be a non-empty string")

	url = url.strip()

	# Parse the URL
	try:
		parsed = urlparse(url)
	except Exception as e:
		raise ValidationError(f"Invalid URL format: {str(e)}")

	# Only allow http and https schemes
	if parsed.scheme not in ('http', 'https'):
		raise ValidationError(
			f"URL scheme '{parsed.scheme}' is not allowed. Only http and https are permitted."
		)

	# Extract hostname (strip port if present)
	hostname = parsed.hostname
	if not hostname:
		raise ValidationError("URL must contain a valid hostname")

	# Block literal 'localhost' hostnames (including subdomains)
	hostname_lower = hostname.lower()
	if hostname_lower == 'localhost' or hostname_lower.endswith('.localhost'):
		raise ValidationError(
			"URLs targeting localhost are not allowed"
		)

	# Resolve hostname to IP addresses and check each one
	try:
		addr_infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
	except socket.gaierror as e:
		raise ValidationError(f"Could not resolve hostname '{hostname}': {str(e)}")

	if not addr_infos:
		raise ValidationError(f"Hostname '{hostname}' did not resolve to any IP address")

	for addr_info in addr_infos:
		# addr_info is (family, type, proto, canonname, sockaddr)
		# sockaddr is (ip, port) for IPv4 or (ip, port, flowinfo, scope_id) for IPv6
		ip_str = addr_info[4][0]

		if _is_ip_blocked(ip_str):
			raise ValidationError(
				f"URL resolves to a blocked IP address ({ip_str}). "
				"Requests to private, loopback, and link-local addresses are not allowed."
			)

	return url


# ---- Convenience functions for common validations ----

def validate_job_data_strict(job_data: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Strictly validate and sanitize job data with comprehensive checks.

	Supports two source types:
	- 'csv': Traditional CSV file source (requires 'source' and 'file_mapping')
	- 'direct_url': Single URL template with optional date/time variables (requires 'url_template')

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

	# Validate source type (default to 'csv' for backwards compatibility)
	source_type = job_data.get('source_type', 'csv')
	validated['source_type'] = validator.validate_source_type(source_type)

	# Validate based on source type
	if source_type == 'direct_url':
		# Direct URL mode - requires url_template
		if 'url_template' not in job_data:
			raise ValidationError("Job with source_type 'direct_url' must have a 'url_template' field")
		validated['url_template'] = validator.validate_url_template(job_data['url_template'])

		# Validate timezone (optional, defaults to UTC)
		validated['timezone'] = validator.validate_timezone(job_data.get('timezone', 'UTC'))

		# source and file_mapping are not required for direct_url mode
	else:
		# CSV mode - requires source and file_mapping
		if 'source' not in job_data:
			raise ValidationError("Job with source_type 'csv' must have a 'source' field")
		validated['source'] = validator.validate_url(job_data['source'], allow_sftp=True)

		if 'file_mapping' not in job_data:
			raise ValidationError("Job with source_type 'csv' must have a 'file_mapping' field")
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

	# Copy proxy_config if present
	if 'proxy_config' in job_data:
		validated['proxy_config'] = job_data['proxy_config']

	# Copy render_config if present
	if 'render_config' in job_data:
		validated['render_config'] = job_data['render_config']

	# Copy user_id if present (added by authentication)
	if 'user_id' in job_data:
		validated['user_id'] = job_data['user_id']

	# Copy job_id if present
	if 'job_id' in job_data:
		validated['job_id'] = job_data['job_id']

	return validated

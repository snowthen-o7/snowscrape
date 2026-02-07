"""
Comprehensive security tests for SnowScrape backend validators.

Tests cover:
- SSRF (Server-Side Request Forgery) protection via validate_scrape_url
- XPath injection prevention via InputValidator.validate_xpath_query
- Regex Denial of Service (ReDoS) prevention via InputValidator.validate_regex_pattern
- Input validation bounds for job names, URL lists, and query selectors
"""

import pytest
from unittest.mock import patch, MagicMock
from validators import (
	ValidationError,
	InputValidator,
	validate_scrape_url,
	_is_ip_blocked,
)


# ---------------------------------------------------------------------------
# SSRF Protection Tests
# ---------------------------------------------------------------------------

class TestSSRFProtection:
	"""Tests for Server-Side Request Forgery protection in validate_scrape_url."""

	# -- Blocked targets --------------------------------------------------

	def test_blocks_localhost(self):
		"""validate_scrape_url should reject http://localhost/..."""
		with pytest.raises(ValidationError, match="localhost"):
			validate_scrape_url("http://localhost/some/path")

	def test_blocks_localhost_https(self):
		"""validate_scrape_url should reject https://localhost/..."""
		with pytest.raises(ValidationError, match="localhost"):
			validate_scrape_url("https://localhost/some/path")

	def test_blocks_localhost_with_port(self):
		"""validate_scrape_url should reject http://localhost:8080/..."""
		with pytest.raises(ValidationError, match="localhost"):
			validate_scrape_url("http://localhost:8080/admin")

	def test_blocks_subdomain_of_localhost(self):
		"""validate_scrape_url should reject http://sub.localhost/..."""
		with pytest.raises(ValidationError, match="localhost"):
			validate_scrape_url("http://sub.localhost/")

	def test_blocks_127_0_0_1(self):
		"""validate_scrape_url should reject http://127.0.0.1/..."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://127.0.0.1/some/path")

	def test_blocks_127_0_0_1_with_port(self):
		"""validate_scrape_url should reject http://127.0.0.1:3000/..."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://127.0.0.1:3000/")

	def test_blocks_127_x_x_x_range(self):
		"""validate_scrape_url should reject any 127.x.x.x address."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://127.0.0.2/")

	def test_blocks_private_10_x(self):
		"""validate_scrape_url should reject http://10.0.0.1/..."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://10.0.0.1/internal")

	def test_blocks_private_10_255_x(self):
		"""validate_scrape_url should reject http://10.255.255.255/..."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://10.255.255.255/")

	def test_blocks_private_172_16_x(self):
		"""validate_scrape_url should reject http://172.16.0.1/..."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://172.16.0.1/")

	def test_blocks_private_172_31_x(self):
		"""validate_scrape_url should reject http://172.31.255.255/..."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://172.31.255.255/")

	def test_blocks_private_192_168_x(self):
		"""validate_scrape_url should reject http://192.168.1.1/..."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://192.168.1.1/router")

	def test_blocks_private_192_168_0_1(self):
		"""validate_scrape_url should reject http://192.168.0.1/..."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://192.168.0.1/")

	def test_blocks_aws_metadata(self):
		"""validate_scrape_url should reject http://169.254.169.254/... (AWS metadata endpoint)."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://169.254.169.254/latest/meta-data/")

	def test_blocks_aws_metadata_with_path(self):
		"""validate_scrape_url should reject AWS metadata with IAM role path."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url(
				"http://169.254.169.254/latest/meta-data/iam/security-credentials/role-name"
			)

	def test_blocks_link_local_range(self):
		"""validate_scrape_url should reject any 169.254.x.x link-local address."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://169.254.1.1/")

	def test_blocks_0_0_0_0(self):
		"""validate_scrape_url should reject http://0.0.0.0/..."""
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://0.0.0.0/")

	# -- Scheme restrictions ----------------------------------------------

	def test_blocks_ftp_scheme(self):
		"""validate_scrape_url should reject ftp://..."""
		with pytest.raises(ValidationError, match="not allowed"):
			validate_scrape_url("ftp://example.com/file.csv")

	def test_blocks_file_scheme(self):
		"""validate_scrape_url should reject file:///..."""
		with pytest.raises(ValidationError, match="not allowed"):
			validate_scrape_url("file:///etc/passwd")

	def test_blocks_gopher_scheme(self):
		"""validate_scrape_url should reject gopher://..."""
		with pytest.raises(ValidationError, match="not allowed"):
			validate_scrape_url("gopher://evil.com/")

	def test_blocks_data_scheme(self):
		"""validate_scrape_url should reject data:... URIs."""
		with pytest.raises(ValidationError, match="not allowed"):
			validate_scrape_url("data:text/html,<h1>hello</h1>")

	def test_blocks_javascript_scheme(self):
		"""validate_scrape_url should reject javascript:... URIs."""
		with pytest.raises(ValidationError, match="not allowed"):
			validate_scrape_url("javascript:alert(1)")

	# -- Empty / invalid inputs -------------------------------------------

	def test_blocks_empty_string(self):
		"""validate_scrape_url should reject empty strings."""
		with pytest.raises(ValidationError, match="non-empty"):
			validate_scrape_url("")

	def test_blocks_none(self):
		"""validate_scrape_url should reject None."""
		with pytest.raises(ValidationError, match="non-empty"):
			validate_scrape_url(None)

	def test_blocks_missing_hostname(self):
		"""validate_scrape_url should reject a URL without a hostname."""
		with pytest.raises(ValidationError):
			validate_scrape_url("http://")

	# -- Allowed public URLs ----------------------------------------------

	@patch("validators.socket.getaddrinfo")
	def test_allows_public_https_url(self, mock_getaddrinfo):
		"""validate_scrape_url should allow https://example.com."""
		# Simulate example.com resolving to a public IP
		mock_getaddrinfo.return_value = [
			(2, 1, 6, "", ("93.184.216.34", 443)),
		]
		result = validate_scrape_url("https://example.com")
		assert result == "https://example.com"

	@patch("validators.socket.getaddrinfo")
	def test_allows_public_http_url(self, mock_getaddrinfo):
		"""validate_scrape_url should allow http://example.com."""
		mock_getaddrinfo.return_value = [
			(2, 1, 6, "", ("93.184.216.34", 80)),
		]
		result = validate_scrape_url("http://example.com")
		assert result == "http://example.com"

	@patch("validators.socket.getaddrinfo")
	def test_allows_public_url_with_path(self, mock_getaddrinfo):
		"""validate_scrape_url should allow public URLs with paths."""
		mock_getaddrinfo.return_value = [
			(2, 1, 6, "", ("93.184.216.34", 443)),
		]
		result = validate_scrape_url("https://example.com/page?q=test")
		assert result == "https://example.com/page?q=test"

	# -- DNS resolution with private IPs (rebinding attack) ---------------

	@patch("validators.socket.getaddrinfo")
	def test_blocks_dns_rebinding_to_127(self, mock_getaddrinfo):
		"""A public hostname resolving to 127.0.0.1 should be blocked."""
		mock_getaddrinfo.return_value = [
			(2, 1, 6, "", ("127.0.0.1", 80)),
		]
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://evil-rebind.example.com/")

	@patch("validators.socket.getaddrinfo")
	def test_blocks_dns_rebinding_to_metadata(self, mock_getaddrinfo):
		"""A public hostname resolving to 169.254.169.254 should be blocked."""
		mock_getaddrinfo.return_value = [
			(2, 1, 6, "", ("169.254.169.254", 80)),
		]
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://rebind-metadata.example.com/")

	@patch("validators.socket.getaddrinfo")
	def test_blocks_if_any_resolved_ip_is_private(self, mock_getaddrinfo):
		"""If a hostname resolves to both public and private IPs, it should be blocked."""
		mock_getaddrinfo.return_value = [
			(2, 1, 6, "", ("93.184.216.34", 80)),
			(2, 1, 6, "", ("10.0.0.1", 80)),
		]
		with pytest.raises(ValidationError, match="blocked IP"):
			validate_scrape_url("http://dual-stack.example.com/")

	@patch("validators.socket.getaddrinfo")
	def test_blocks_unresolvable_hostname(self, mock_getaddrinfo):
		"""A hostname that cannot be resolved should be rejected."""
		import socket
		mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")
		with pytest.raises(ValidationError, match="Could not resolve"):
			validate_scrape_url("http://nonexistent.invalid/")


# ---------------------------------------------------------------------------
# Helper: _is_ip_blocked unit tests
# ---------------------------------------------------------------------------

class TestIsIPBlocked:
	"""Direct unit tests for the _is_ip_blocked helper."""

	def test_loopback_v4(self):
		assert _is_ip_blocked("127.0.0.1") is True

	def test_private_class_a(self):
		assert _is_ip_blocked("10.1.2.3") is True

	def test_private_class_b(self):
		assert _is_ip_blocked("172.20.0.1") is True

	def test_private_class_c(self):
		assert _is_ip_blocked("192.168.100.5") is True

	def test_link_local(self):
		assert _is_ip_blocked("169.254.169.254") is True

	def test_public_ip_allowed(self):
		assert _is_ip_blocked("93.184.216.34") is False

	def test_another_public_ip(self):
		assert _is_ip_blocked("8.8.8.8") is False

	def test_loopback_v6(self):
		assert _is_ip_blocked("::1") is True

	def test_unique_local_v6(self):
		assert _is_ip_blocked("fc00::1") is True

	def test_link_local_v6(self):
		assert _is_ip_blocked("fe80::1") is True

	def test_invalid_ip_string_blocked(self):
		"""An unparseable IP string should be treated as blocked (fail-safe)."""
		assert _is_ip_blocked("not-an-ip") is True

	def test_empty_string_blocked(self):
		assert _is_ip_blocked("") is True


# ---------------------------------------------------------------------------
# XPath Validation Tests
# ---------------------------------------------------------------------------

class TestXPathValidation:
	"""Tests for XPath injection prevention in InputValidator.validate_xpath_query."""

	# -- Allowed expressions ----------------------------------------------

	def test_allows_safe_xpath(self):
		"""//div/text() should be allowed."""
		result = InputValidator.validate_xpath_query("//div/text()")
		assert result == "//div/text()"

	def test_allows_contains(self):
		"""//div[contains(@class, 'content')] should be allowed."""
		result = InputValidator.validate_xpath_query(
			"//div[contains(@class, 'content')]"
		)
		assert "contains" in result

	def test_allows_starts_with(self):
		"""starts-with() is a whitelisted function."""
		result = InputValidator.validate_xpath_query(
			"//a[starts-with(@href, '/products')]"
		)
		assert "starts-with" in result

	def test_allows_position(self):
		"""position() is a whitelisted function."""
		result = InputValidator.validate_xpath_query(
			"//li[position() <= 5]"
		)
		assert "position" in result

	def test_allows_not_function(self):
		"""not() is a whitelisted function."""
		result = InputValidator.validate_xpath_query(
			"//div[not(contains(@class, 'hidden'))]"
		)
		assert "not" in result

	def test_allows_concat(self):
		"""concat() is a whitelisted function."""
		result = InputValidator.validate_xpath_query(
			"//span[concat('a', 'b')]"
		)
		assert "concat" in result

	def test_allows_string_length(self):
		"""string-length() is a whitelisted function."""
		result = InputValidator.validate_xpath_query(
			"//input[string-length(@value) > 0]"
		)
		assert "string-length" in result

	def test_allows_normalize_space(self):
		"""normalize-space() is a whitelisted function."""
		result = InputValidator.validate_xpath_query(
			"//p[normalize-space()]"
		)
		assert "normalize-space" in result

	def test_allows_last(self):
		"""last() is a whitelisted function."""
		result = InputValidator.validate_xpath_query(
			"//item[last()]"
		)
		assert "last" in result

	def test_allows_count(self):
		"""count() is a whitelisted function."""
		result = InputValidator.validate_xpath_query(
			"//ul[count(li) > 3]"
		)
		assert "count" in result

	def test_allows_simple_path_no_functions(self):
		"""A simple path with no function calls should be allowed."""
		result = InputValidator.validate_xpath_query("//body/div/span/@class")
		assert result == "//body/div/span/@class"

	# -- Blocked expressions (dangerous functions) ------------------------

	def test_blocks_document_function(self):
		"""document() is not whitelisted and should be blocked."""
		with pytest.raises(ValidationError, match="not allowed"):
			InputValidator.validate_xpath_query(
				"//div[document('evil.xml')]"
			)

	def test_blocks_system_property(self):
		"""system-property() should be blocked."""
		with pytest.raises(ValidationError, match="not allowed"):
			InputValidator.validate_xpath_query(
				"//div[system-property('xsl:version')]"
			)

	def test_blocks_unknown_function(self):
		"""An unknown/arbitrary function should be blocked."""
		with pytest.raises(ValidationError, match="not allowed"):
			InputValidator.validate_xpath_query(
				"//div[evil-func()]"
			)

	def test_blocks_unparsed_entity_uri(self):
		"""unparsed-entity-uri() should be blocked."""
		with pytest.raises(ValidationError, match="not allowed"):
			InputValidator.validate_xpath_query(
				"//div[unparsed-entity-uri('foo')]"
			)

	def test_blocks_generate_id(self):
		"""generate-id() should be blocked."""
		with pytest.raises(ValidationError, match="not allowed"):
			InputValidator.validate_xpath_query(
				"//div[generate-id()]"
			)

	def test_blocks_key_function(self):
		"""key() should be blocked."""
		with pytest.raises(ValidationError, match="not allowed"):
			InputValidator.validate_xpath_query(
				"//div[key('mykey', 'value')]"
			)

	def test_blocks_format_number(self):
		"""format-number() should be blocked."""
		with pytest.raises(ValidationError, match="not allowed"):
			InputValidator.validate_xpath_query(
				"//div[format-number(1234, '#,###')]"
			)

	# -- Length / size limits ---------------------------------------------

	def test_blocks_oversized_expression(self):
		"""An XPath expression > 1000 characters should be blocked."""
		long_xpath = "//div" + "/child" * 200  # well over 1000 chars
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_xpath_query(long_xpath)

	def test_allows_expression_at_max_length(self):
		"""An XPath expression exactly at 1000 characters should be allowed."""
		# Build an expression of exactly 1000 characters
		# "//div" = 5 chars, "/a" = 2 chars each; 5 + 2*N = 1000 is not exact
		# so we use a single-char filler path to hit exactly 1000
		xpath = "/" * 1000
		assert len(xpath) == 1000
		result = InputValidator.validate_xpath_query(xpath)
		assert len(result) == 1000

	# -- Structural validation --------------------------------------------

	def test_blocks_unbalanced_brackets(self):
		"""Unbalanced square brackets should be rejected."""
		with pytest.raises(ValidationError, match="unbalanced brackets"):
			InputValidator.validate_xpath_query("//div[contains(@class, 'a')")

	def test_blocks_unbalanced_parentheses(self):
		"""Unbalanced parentheses should be rejected."""
		with pytest.raises(ValidationError, match="unbalanced parentheses"):
			InputValidator.validate_xpath_query("//div[contains(@class, 'a']")

	def test_blocks_excessive_nesting(self):
		"""Excessive nesting depth (>20 levels) should be rejected."""
		# 25 levels of nested brackets
		xpath = "//div" + "[" * 25 + "text()" + "]" * 25
		with pytest.raises(ValidationError, match="excessive nesting"):
			InputValidator.validate_xpath_query(xpath)

	# -- Empty / invalid inputs -------------------------------------------

	def test_blocks_empty_xpath(self):
		"""Empty XPath should be rejected."""
		with pytest.raises(ValidationError, match="non-empty"):
			InputValidator.validate_xpath_query("")

	def test_blocks_none_xpath(self):
		"""None XPath should be rejected."""
		with pytest.raises(ValidationError, match="non-empty"):
			InputValidator.validate_xpath_query(None)

	def test_whitespace_only_xpath_returns_empty(self):
		"""Whitespace-only XPath is stripped; the validator does not re-check emptiness after strip.

		Note: The current implementation strips whitespace but does not reject the
		resulting empty string. This test documents the actual behavior. If the
		validator is tightened in the future, this test should be updated to expect
		a ValidationError.
		"""
		result = InputValidator.validate_xpath_query("   ")
		assert result == ""


# ---------------------------------------------------------------------------
# Regex Validation Tests
# ---------------------------------------------------------------------------

class TestRegexValidation:
	"""Tests for ReDoS prevention in InputValidator.validate_regex_pattern."""

	# -- Allowed patterns -------------------------------------------------

	def test_allows_simple_pattern(self):
		r"""r'\d{3}-\d{4}' should be allowed."""
		result = InputValidator.validate_regex_pattern(r"\d{3}-\d{4}")
		assert result == r"\d{3}-\d{4}"

	def test_allows_email_pattern(self):
		"""A common email regex should be allowed."""
		pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
		result = InputValidator.validate_regex_pattern(pattern)
		assert result == pattern

	def test_allows_url_pattern(self):
		"""A simple URL pattern should be allowed."""
		pattern = r"https?://[^\s]+"
		result = InputValidator.validate_regex_pattern(pattern)
		assert result == pattern

	def test_allows_phone_pattern(self):
		"""A US phone number pattern should be allowed."""
		pattern = r"\(\d{3}\)\s?\d{3}-\d{4}"
		result = InputValidator.validate_regex_pattern(pattern)
		assert result == pattern

	def test_allows_simple_alternation(self):
		"""Simple alternation without overlap should be allowed."""
		pattern = r"(cat|dog)"
		result = InputValidator.validate_regex_pattern(pattern)
		assert result == r"(cat|dog)"

	def test_allows_character_class(self):
		"""Character classes should be allowed."""
		pattern = r"[A-Za-z0-9_]+"
		result = InputValidator.validate_regex_pattern(pattern)
		assert result == pattern

	# -- Blocked: catastrophic backtracking patterns ----------------------

	def test_blocks_nested_quantifiers_plus_plus(self):
		"""(a+)+ should be blocked (nested quantifiers)."""
		with pytest.raises(ValidationError, match="catastrophic backtracking"):
			InputValidator.validate_regex_pattern(r"(a+)+")

	def test_blocks_nested_quantifiers_star_star(self):
		"""(a*)* should be blocked (nested quantifiers)."""
		with pytest.raises(ValidationError, match="catastrophic backtracking"):
			InputValidator.validate_regex_pattern(r"(a*)*")

	def test_blocks_nested_quantifiers_plus_star(self):
		"""(a+)* should be blocked (nested quantifiers)."""
		with pytest.raises(ValidationError, match="catastrophic backtracking"):
			InputValidator.validate_regex_pattern(r"(a+)*")

	def test_blocks_nested_quantifiers_star_plus(self):
		"""(a*)+ should be blocked (nested quantifiers)."""
		with pytest.raises(ValidationError, match="catastrophic backtracking"):
			InputValidator.validate_regex_pattern(r"(a*)+")

	def test_blocks_overlapping_alternation(self):
		"""(a|ab) should be blocked (overlapping alternation)."""
		with pytest.raises(ValidationError, match="catastrophic backtracking"):
			InputValidator.validate_regex_pattern(r"(a|ab)")

	def test_blocks_identical_alternation(self):
		"""(a|a) should be blocked (identical alternatives)."""
		with pytest.raises(ValidationError, match="catastrophic backtracking"):
			InputValidator.validate_regex_pattern(r"(a|a)")

	def test_blocks_quantified_alternation_group(self):
		"""(a+|b+)+ should be blocked (quantified group with quantified alternation)."""
		with pytest.raises(ValidationError, match="catastrophic backtracking"):
			InputValidator.validate_regex_pattern(r"(a+|b+)+")

	# -- Blocked: oversized patterns --------------------------------------

	def test_blocks_oversized_pattern(self):
		"""A pattern > 500 characters should be blocked."""
		long_pattern = "a" * 501
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_regex_pattern(long_pattern)

	def test_allows_pattern_at_max_length(self):
		"""A pattern of exactly 500 characters should be allowed."""
		pattern = "a" * 500
		result = InputValidator.validate_regex_pattern(pattern)
		assert len(result) == 500

	# -- Blocked: too many quantifiers ------------------------------------

	def test_blocks_excessive_quantifiers(self):
		"""A pattern with more than 5 quantifiers should be blocked."""
		# 6 quantifiers: a+ b+ c+ d+ e+ f+
		pattern = r"a+b+c+d+e+f+"
		with pytest.raises(ValidationError, match="too complex"):
			InputValidator.validate_regex_pattern(pattern)

	def test_allows_five_quantifiers(self):
		"""A pattern with exactly 5 quantifiers should be allowed."""
		pattern = r"a+b+c+d+e+"
		result = InputValidator.validate_regex_pattern(pattern)
		assert result == pattern

	# -- Invalid syntax ---------------------------------------------------

	def test_blocks_invalid_regex_syntax(self):
		"""An invalid regex should be rejected."""
		with pytest.raises(ValidationError, match="Invalid regex"):
			InputValidator.validate_regex_pattern(r"(unclosed group")

	def test_blocks_invalid_quantifier_syntax(self):
		"""A regex with invalid repetition should be rejected."""
		with pytest.raises(ValidationError, match="Invalid regex"):
			InputValidator.validate_regex_pattern(r"*invalid")

	# -- Empty / invalid inputs -------------------------------------------

	def test_blocks_empty_pattern(self):
		"""Empty pattern should be rejected."""
		with pytest.raises(ValidationError, match="non-empty"):
			InputValidator.validate_regex_pattern("")

	def test_blocks_none_pattern(self):
		"""None pattern should be rejected."""
		with pytest.raises(ValidationError, match="non-empty"):
			InputValidator.validate_regex_pattern(None)


# ---------------------------------------------------------------------------
# Input Validation Tests
# ---------------------------------------------------------------------------

class TestInputValidation:
	"""Tests for general input validation bounds and limits."""

	# -- Job name validation ----------------------------------------------

	def test_job_name_max_length_exceeded(self):
		"""Job names exceeding MAX_JOB_NAME_LENGTH (200) should be rejected."""
		long_name = "A" * 201
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_job_name(long_name)

	def test_job_name_at_max_length(self):
		"""Job names at exactly 200 characters should be accepted."""
		name = "A" * 200
		result = InputValidator.validate_job_name(name)
		assert len(result) == 200

	def test_job_name_empty_rejected(self):
		"""Empty job names should be rejected."""
		with pytest.raises(ValidationError, match="non-empty"):
			InputValidator.validate_job_name("")

	def test_job_name_none_rejected(self):
		"""None job names should be rejected."""
		with pytest.raises(ValidationError, match="non-empty"):
			InputValidator.validate_job_name(None)

	def test_job_name_whitespace_only_rejected(self):
		"""Whitespace-only job names should be rejected."""
		with pytest.raises(ValidationError, match="empty or whitespace"):
			InputValidator.validate_job_name("   ")

	def test_job_name_strips_whitespace(self):
		"""Job names should have leading/trailing whitespace stripped."""
		result = InputValidator.validate_job_name("  My Job  ")
		assert result == "My Job"

	def test_job_name_normalizes_internal_whitespace(self):
		"""Multiple internal spaces should be collapsed to single space."""
		result = InputValidator.validate_job_name("My    Job    Name")
		assert result == "My Job Name"

	def test_job_name_removes_control_characters(self):
		"""Control characters should be stripped from job names."""
		result = InputValidator.validate_job_name("My\x00Job\x01Name")
		assert "\x00" not in result
		assert "\x01" not in result

	# -- URL list validation ----------------------------------------------

	def test_url_list_max_count_exceeded(self):
		"""URL lists exceeding MAX_URLS_PER_JOB (10000) should be rejected."""
		urls = [f"https://example.com/page/{i}" for i in range(10001)]
		with pytest.raises(ValidationError, match="maximum"):
			InputValidator.validate_url_list(urls)

	def test_url_list_custom_max_count_exceeded(self):
		"""URL lists exceeding a custom max_count should be rejected."""
		urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
		with pytest.raises(ValidationError, match="maximum"):
			InputValidator.validate_url_list(urls, max_count=2)

	def test_url_list_empty_rejected(self):
		"""Empty URL lists should be rejected."""
		with pytest.raises(ValidationError, match="cannot be empty"):
			InputValidator.validate_url_list([])

	def test_url_list_not_a_list_rejected(self):
		"""Non-list URL inputs should be rejected."""
		with pytest.raises(ValidationError, match="must be provided as a list"):
			InputValidator.validate_url_list("https://example.com")

	def test_url_list_duplicate_urls_rejected(self):
		"""Duplicate URLs in the list should be rejected."""
		urls = ["https://example.com/page", "https://example.com/page"]
		with pytest.raises(ValidationError, match="Duplicate"):
			InputValidator.validate_url_list(urls)

	def test_url_list_invalid_url_in_list(self):
		"""An invalid URL in the list should cause rejection."""
		urls = ["https://example.com/page", "not-a-url"]
		with pytest.raises(ValidationError, match="Invalid URL"):
			InputValidator.validate_url_list(urls)

	# -- Query selector length validation ---------------------------------

	def test_query_selector_max_length_xpath(self):
		"""XPath selectors exceeding MAX_XPATH_LENGTH (1000) should be rejected."""
		long_xpath = "//div" + "/child" * 200
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_xpath_query(long_xpath)

	def test_query_selector_max_length_jsonpath(self):
		"""JSONPath selectors exceeding MAX_QUERY_SELECTOR_LENGTH (1000) should be rejected."""
		long_jsonpath = "$" + ".field" * 200
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_jsonpath_query(long_jsonpath)

	def test_query_selector_max_length_regex(self):
		"""Regex selectors exceeding MAX_REGEX_PATTERN_LENGTH (500) should be rejected."""
		long_regex = "a" * 501
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_regex_pattern(long_regex)

	# -- Query name validation --------------------------------------------

	def test_query_name_max_length(self):
		"""Query names exceeding MAX_QUERY_NAME_LENGTH (100) should be rejected."""
		query = {
			"name": "a" * 101,
			"type": "xpath",
			"selector": "//div/text()"
		}
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_query(query)

	def test_query_name_special_characters_rejected(self):
		"""Query names with special characters (beyond alphanumeric, _, -) should be rejected."""
		query = {
			"name": "my query!",
			"type": "xpath",
			"selector": "//div/text()"
		}
		with pytest.raises(ValidationError, match="letters, numbers, underscores"):
			InputValidator.validate_query(query)

	def test_query_name_valid_characters(self):
		"""Query names with valid characters should be accepted."""
		query = {
			"name": "my_query-1",
			"type": "xpath",
			"selector": "//div/text()"
		}
		result = InputValidator.validate_query(query)
		assert result["name"] == "my_query-1"

	# -- Queries list validation ------------------------------------------

	def test_queries_max_count_exceeded(self):
		"""More than MAX_QUERIES_PER_JOB (50) queries should be rejected."""
		queries = [
			{
				"name": f"query_{i}",
				"type": "xpath",
				"selector": "//div/text()"
			}
			for i in range(51)
		]
		with pytest.raises(ValidationError, match="Maximum"):
			InputValidator.validate_queries(queries)

	def test_queries_duplicate_names_rejected(self):
		"""Queries with duplicate names should be rejected."""
		queries = [
			{"name": "title", "type": "xpath", "selector": "//title/text()"},
			{"name": "title", "type": "xpath", "selector": "//h1/text()"},
		]
		with pytest.raises(ValidationError, match="Duplicate query name"):
			InputValidator.validate_queries(queries)

	def test_queries_empty_list_rejected(self):
		"""An empty queries list should be rejected."""
		with pytest.raises(ValidationError, match="At least one query"):
			InputValidator.validate_queries([])

	# -- URL validation (InputValidator.validate_url) ---------------------

	def test_url_max_length_exceeded(self):
		"""URLs exceeding MAX_URL_LENGTH (2048) should be rejected."""
		long_url = "https://example.com/" + "a" * 2040
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_url(long_url)

	def test_url_empty_rejected(self):
		"""Empty URL should be rejected."""
		with pytest.raises(ValidationError, match="non-empty"):
			InputValidator.validate_url("")

	def test_url_ftp_not_allowed_by_default(self):
		"""FTP is not in the default allowed schemes (http, https, sftp)."""
		with pytest.raises(ValidationError, match="scheme"):
			InputValidator.validate_url("ftp://example.com/file")

	def test_url_sftp_allowed_by_default(self):
		"""SFTP should be allowed when allow_sftp=True (default)."""
		result = InputValidator.validate_url("sftp://example.com/file.csv")
		assert result.startswith("sftp://")

	def test_url_sftp_rejected_when_disabled(self):
		"""SFTP should be rejected when allow_sftp=False."""
		with pytest.raises(ValidationError, match="scheme"):
			InputValidator.validate_url("sftp://example.com/file.csv", allow_sftp=False)

	# -- Rate limit validation --------------------------------------------

	def test_rate_limit_below_minimum(self):
		"""Rate limit below 1 should be rejected."""
		with pytest.raises(ValidationError, match="between 1 and 8"):
			InputValidator.validate_rate_limit(0)

	def test_rate_limit_above_maximum(self):
		"""Rate limit above 8 should be rejected."""
		with pytest.raises(ValidationError, match="between 1 and 8"):
			InputValidator.validate_rate_limit(9)

	def test_rate_limit_not_integer(self):
		"""Non-integer rate limit should be rejected."""
		with pytest.raises(ValidationError, match="must be an integer"):
			InputValidator.validate_rate_limit("5")

	def test_rate_limit_valid_range(self):
		"""Rate limits 1-8 should be accepted."""
		for i in range(1, 9):
			assert InputValidator.validate_rate_limit(i) == i


# ---------------------------------------------------------------------------
# Full Job Data Strict Validation (integration of all validators)
# ---------------------------------------------------------------------------

class TestJobDataStrictValidation:
	"""Tests for validate_job_data_strict combining multiple validators."""

	def _base_job_data(self):
		"""Return a minimal valid job data dict for CSV source type."""
		return {
			"name": "Test Job",
			"source_type": "csv",
			"source": "https://example.com/urls.csv",
			"file_mapping": {
				"delimiter": ",",
				"enclosure": '"',
				"escape": "\\",
				"url_column": 0,
			},
			"queries": [
				{
					"name": "title",
					"type": "xpath",
					"selector": "//title/text()",
					"join": False,
				}
			],
			"rate_limit": 5,
		}

	def test_valid_csv_job_passes(self):
		"""A fully valid CSV job should pass strict validation."""
		from validators import validate_job_data_strict

		data = self._base_job_data()
		result = validate_job_data_strict(data)
		assert result["name"] == "Test Job"
		assert result["source_type"] == "csv"

	def test_missing_name_rejected(self):
		"""Missing name field should be rejected."""
		from validators import validate_job_data_strict

		data = self._base_job_data()
		del data["name"]
		with pytest.raises(ValidationError, match="name"):
			validate_job_data_strict(data)

	def test_missing_queries_rejected(self):
		"""Missing queries field should be rejected."""
		from validators import validate_job_data_strict

		data = self._base_job_data()
		del data["queries"]
		with pytest.raises(ValidationError, match="queries"):
			validate_job_data_strict(data)

	def test_missing_rate_limit_rejected(self):
		"""Missing rate_limit field should be rejected."""
		from validators import validate_job_data_strict

		data = self._base_job_data()
		del data["rate_limit"]
		with pytest.raises(ValidationError, match="rate_limit"):
			validate_job_data_strict(data)

	def test_csv_mode_missing_source_rejected(self):
		"""CSV mode without source field should be rejected."""
		from validators import validate_job_data_strict

		data = self._base_job_data()
		del data["source"]
		with pytest.raises(ValidationError, match="source"):
			validate_job_data_strict(data)

	def test_csv_mode_missing_file_mapping_rejected(self):
		"""CSV mode without file_mapping field should be rejected."""
		from validators import validate_job_data_strict

		data = self._base_job_data()
		del data["file_mapping"]
		with pytest.raises(ValidationError, match="file_mapping"):
			validate_job_data_strict(data)

	def test_invalid_rate_limit_in_job_data(self):
		"""Invalid rate_limit in full job data should be rejected."""
		from validators import validate_job_data_strict

		data = self._base_job_data()
		data["rate_limit"] = 99
		with pytest.raises(ValidationError, match="between 1 and 8"):
			validate_job_data_strict(data)

	def test_dangerous_xpath_in_query_rejected(self):
		"""A query with a dangerous XPath function should be rejected."""
		from validators import validate_job_data_strict

		data = self._base_job_data()
		data["queries"] = [
			{
				"name": "evil",
				"type": "xpath",
				"selector": "//div[document('evil.xml')]",
				"join": False,
			}
		]
		with pytest.raises(ValidationError, match="not allowed"):
			validate_job_data_strict(data)

	def test_redos_pattern_in_query_rejected(self):
		"""A query with a ReDoS-vulnerable regex should be rejected."""
		from validators import validate_job_data_strict

		data = self._base_job_data()
		data["queries"] = [
			{
				"name": "bad-regex",
				"type": "regex",
				"selector": "(a+)+b",
				"join": False,
			}
		]
		with pytest.raises(ValidationError, match="catastrophic backtracking"):
			validate_job_data_strict(data)

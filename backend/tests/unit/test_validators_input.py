"""
Characterization tests for the untested InputValidator job-config validators.

test_security.py already covers the security-critical surfaces (SSRF via
validate_scrape_url, XPath whitelist, ReDoS regex bounds, job-name/url-list
bounds, validate_job_data_strict). This file pins the remaining job-create
validators that had no dedicated coverage:

- validate_jsonpath_query  (query type 'jsonpath')
- validate_file_mapping    (csv source column mapping)
- sanitize_string          (generic control-char/length scrub)
- validate_url_template    (scheduled/direct_url templated targets)
- validate_source_type     ('csv' | 'direct_url')

These are pure/deterministic and sit on the live job-create validation path,
so they are regression-hardening characterization tests (no source change).
"""

import pytest

from validators import ValidationError, InputValidator


# ---------------------------------------------------------------------------
# validate_jsonpath_query
# ---------------------------------------------------------------------------

class TestValidateJsonPathQuery:
	"""InputValidator.validate_jsonpath_query."""

	def test_accepts_dollar_rooted_query(self):
		assert InputValidator.validate_jsonpath_query("$.store.book[0].title") == "$.store.book[0].title"

	def test_accepts_at_rooted_query(self):
		assert InputValidator.validate_jsonpath_query("@.price") == "@.price"

	def test_strips_surrounding_whitespace(self):
		assert InputValidator.validate_jsonpath_query("  $.a.b  ") == "$.a.b"

	def test_rejects_empty_string(self):
		with pytest.raises(ValidationError, match="non-empty string"):
			InputValidator.validate_jsonpath_query("")

	def test_rejects_non_string(self):
		with pytest.raises(ValidationError, match="non-empty string"):
			InputValidator.validate_jsonpath_query(None)  # type: ignore[arg-type]

	def test_rejects_query_not_starting_with_dollar_or_at(self):
		with pytest.raises(ValidationError, match=r"must start with"):
			InputValidator.validate_jsonpath_query("store.book")

	def test_rejects_unbalanced_brackets(self):
		with pytest.raises(ValidationError, match="unbalanced brackets"):
			InputValidator.validate_jsonpath_query("$.book[0")

	def test_rejects_overlong_query(self):
		too_long = "$." + ("a" * (InputValidator.MAX_QUERY_SELECTOR_LENGTH + 1))
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_jsonpath_query(too_long)


# ---------------------------------------------------------------------------
# validate_file_mapping
# ---------------------------------------------------------------------------

def _valid_mapping(**overrides):
	mapping = {
		"delimiter": ",",
		"enclosure": '"',
		"escape": "\\",
		"url_column": "default",
	}
	mapping.update(overrides)
	return mapping


class TestValidateFileMapping:
	"""InputValidator.validate_file_mapping."""

	def test_accepts_a_well_formed_mapping(self):
		mapping = _valid_mapping()
		assert InputValidator.validate_file_mapping(mapping) == mapping

	def test_rejects_non_dict(self):
		with pytest.raises(ValidationError, match="must be a dictionary"):
			InputValidator.validate_file_mapping(["not", "a", "dict"])  # type: ignore[arg-type]

	@pytest.mark.parametrize("missing", ["delimiter", "enclosure", "escape", "url_column"])
	def test_rejects_missing_required_key(self, missing):
		mapping = _valid_mapping()
		del mapping[missing]
		with pytest.raises(ValidationError, match=f"must contain '{missing}'"):
			InputValidator.validate_file_mapping(mapping)

	@pytest.mark.parametrize("delimiter", [",", ";", "|", "\t", "\\t"])
	def test_accepts_each_valid_delimiter(self, delimiter):
		mapping = _valid_mapping(delimiter=delimiter)
		assert InputValidator.validate_file_mapping(mapping)["delimiter"] == delimiter

	def test_rejects_unknown_delimiter(self):
		with pytest.raises(ValidationError, match="Invalid delimiter"):
			InputValidator.validate_file_mapping(_valid_mapping(delimiter="::"))

	@pytest.mark.parametrize("enclosure", ['"', "'", "none"])
	def test_accepts_each_valid_enclosure(self, enclosure):
		assert InputValidator.validate_file_mapping(_valid_mapping(enclosure=enclosure))["enclosure"] == enclosure

	def test_rejects_unknown_enclosure(self):
		with pytest.raises(ValidationError, match="Invalid enclosure"):
			InputValidator.validate_file_mapping(_valid_mapping(enclosure="`"))

	@pytest.mark.parametrize("escape", ["\\", "/", '"', "'", "none"])
	def test_accepts_each_valid_escape(self, escape):
		assert InputValidator.validate_file_mapping(_valid_mapping(escape=escape))["escape"] == escape

	def test_rejects_unknown_escape(self):
		with pytest.raises(ValidationError, match="Invalid escape"):
			InputValidator.validate_file_mapping(_valid_mapping(escape="^"))

	def test_accepts_integer_url_column_in_range(self):
		assert InputValidator.validate_file_mapping(_valid_mapping(url_column=0))["url_column"] == 0
		assert InputValidator.validate_file_mapping(_valid_mapping(url_column=100))["url_column"] == 100

	@pytest.mark.parametrize("col", [-1, 101])
	def test_rejects_integer_url_column_out_of_range(self, col):
		with pytest.raises(ValidationError, match="between 0 and 100"):
			InputValidator.validate_file_mapping(_valid_mapping(url_column=col))

	def test_accepts_named_url_column(self):
		assert InputValidator.validate_file_mapping(_valid_mapping(url_column="product_url"))["url_column"] == "product_url"

	def test_rejects_named_url_column_with_illegal_chars(self):
		with pytest.raises(ValidationError, match="letters, numbers, underscores, and hyphens"):
			InputValidator.validate_file_mapping(_valid_mapping(url_column="bad col!"))

	def test_rejects_url_column_of_wrong_type(self):
		with pytest.raises(ValidationError, match="integer index or string name"):
			InputValidator.validate_file_mapping(_valid_mapping(url_column=1.5))

	def test_bool_url_column_is_treated_as_int_index(self):
		# Python gotcha: isinstance(True, int) is True, so a bool falls into the
		# 0-100 index branch (True -> 1, False -> 0) rather than being rejected.
		# Pinned to characterize the current behavior, not to bless it.
		assert InputValidator.validate_file_mapping(_valid_mapping(url_column=True))["url_column"] is True
		assert InputValidator.validate_file_mapping(_valid_mapping(url_column=False))["url_column"] is False


# ---------------------------------------------------------------------------
# sanitize_string
# ---------------------------------------------------------------------------

class TestSanitizeString:
	"""InputValidator.sanitize_string."""

	def test_passes_through_a_clean_string(self):
		assert InputValidator.sanitize_string("hello world") == "hello world"

	def test_trims_surrounding_whitespace(self):
		assert InputValidator.sanitize_string("  padded  ") == "padded"

	def test_strips_control_characters(self):
		assert InputValidator.sanitize_string("a\x00b\x07c") == "abc"

	def test_strips_carriage_return(self):
		# \r (ord 13) is NOT in the preserved set (only \n and \t are), so it is stripped.
		assert InputValidator.sanitize_string("a\rb") == "ab"

	def test_preserves_newlines_and_tabs(self):
		assert InputValidator.sanitize_string("line1\nline2\tend") == "line1\nline2\tend"

	def test_rejects_non_string(self):
		with pytest.raises(ValidationError, match="must be a string"):
			InputValidator.sanitize_string(123)  # type: ignore[arg-type]

	def test_enforces_max_length_when_provided(self):
		with pytest.raises(ValidationError, match="maximum length of 5"):
			InputValidator.sanitize_string("abcdef", max_length=5)

	def test_allows_value_at_max_length(self):
		assert InputValidator.sanitize_string("abcde", max_length=5) == "abcde"

	def test_no_length_check_without_max_length(self):
		long_value = "x" * 10000
		assert InputValidator.sanitize_string(long_value) == long_value

	def test_max_length_zero_is_falsy_and_disables_the_check(self):
		# Python gotcha: the guard is `if max_length and ...`, so max_length=0 is
		# falsy and disables the length check entirely (does NOT reject all input).
		assert InputValidator.sanitize_string("abc", max_length=0) == "abc"


# ---------------------------------------------------------------------------
# validate_source_type
# ---------------------------------------------------------------------------

class TestValidateSourceType:
	"""InputValidator.validate_source_type."""

	@pytest.mark.parametrize("source_type", ["csv", "direct_url"])
	def test_accepts_valid_source_types(self, source_type):
		assert InputValidator.validate_source_type(source_type) == source_type

	@pytest.mark.parametrize("bad", ["", "CSV", "url", "direct", "json", None])
	def test_rejects_invalid_source_types(self, bad):
		with pytest.raises(ValidationError, match="Source type must be one of"):
			InputValidator.validate_source_type(bad)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# validate_url_template
# ---------------------------------------------------------------------------

class TestValidateUrlTemplate:
	"""InputValidator.validate_url_template."""

	def test_accepts_a_plain_http_url(self):
		assert InputValidator.validate_url_template("https://example.com/products") == "https://example.com/products"

	def test_accepts_a_templated_url(self):
		template = "https://example.com/feed/{{date:Y-m-d}}"
		assert InputValidator.validate_url_template(template) == template

	def test_strips_surrounding_whitespace(self):
		assert InputValidator.validate_url_template("  https://example.com  ") == "https://example.com"

	def test_rejects_empty_string(self):
		with pytest.raises(ValidationError, match="non-empty string"):
			InputValidator.validate_url_template("")

	def test_rejects_non_string(self):
		with pytest.raises(ValidationError, match="non-empty string"):
			InputValidator.validate_url_template(None)  # type: ignore[arg-type]

	def test_rejects_overlong_template(self):
		too_long = "https://example.com/" + ("a" * InputValidator.MAX_URL_LENGTH)
		with pytest.raises(ValidationError, match="maximum length"):
			InputValidator.validate_url_template(too_long)

	def test_rejects_non_http_scheme(self):
		with pytest.raises(ValidationError, match="scheme must be one of"):
			InputValidator.validate_url_template("ftp://example.com/file")

	def test_rejects_url_without_hostname(self):
		# Non-empty, valid template + scheme, but urlparse yields an empty netloc.
		with pytest.raises(ValidationError, match="valid hostname"):
			InputValidator.validate_url_template("https://")

	def test_rejects_unmatched_template_braces(self):
		# Short-circuits on the unmatched-braces branch in the resolver.
		with pytest.raises(ValidationError, match="Invalid URL template"):
			InputValidator.validate_url_template("https://example.com/{{date")

	def test_rejects_unknown_template_variable(self):
		# Brace-balanced but not a date/time variable: hits the variable-syntax branch.
		with pytest.raises(ValidationError, match="Invalid URL template"):
			InputValidator.validate_url_template("https://example.com/{{notavar}}")

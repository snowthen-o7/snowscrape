"""Unit tests for docs_formatter."""
import pytest


def test_structured_log_emits_heading_per_row():
	from docs_formatter import format_rows_to_docs_requests

	rows = [
		{"url": "https://a.example/post/1", "title": "First post", "body": "Hello"},
		{"url": "https://a.example/post/2", "title": "Second post", "body": "World"},
	]

	requests = format_rows_to_docs_requests(
		rows=rows,
		format_template="structured_log",
		title="My Job — 2026-06-01",
	)

	assert any(
		"insertText" in r and "My Job — 2026-06-01" in r["insertText"]["text"]
		for r in requests
	)
	assert any("First post" in r.get("insertText", {}).get("text", "") for r in requests)
	assert any("Second post" in r.get("insertText", {}).get("text", "") for r in requests)
	assert any("updateParagraphStyle" in r for r in requests)


def test_compact_list_one_line_per_row():
	from docs_formatter import format_rows_to_docs_requests

	rows = [
		{"url": "https://a/1", "title": "A"},
		{"url": "https://a/2", "title": "B"},
	]

	requests = format_rows_to_docs_requests(
		rows=rows,
		format_template="compact_list",
		title="Compact",
	)

	full_text = "".join(
		r.get("insertText", {}).get("text", "") for r in requests
	)
	assert "A" in full_text
	assert "B" in full_text
	assert full_text.count("\n") <= len(rows) + 3


def test_narrative_concatenates_body_fields():
	from docs_formatter import format_rows_to_docs_requests

	rows = [
		{"body": "Paragraph one."},
		{"body": "Paragraph two."},
	]

	requests = format_rows_to_docs_requests(
		rows=rows,
		format_template="narrative",
		title="Narrative",
	)

	full_text = "".join(
		r.get("insertText", {}).get("text", "") for r in requests
	)
	assert "Paragraph one." in full_text
	assert "Paragraph two." in full_text


def test_empty_rows_still_produces_title():
	from docs_formatter import format_rows_to_docs_requests

	requests = format_rows_to_docs_requests(
		rows=[],
		format_template="structured_log",
		title="Empty Job",
	)

	full_text = "".join(
		r.get("insertText", {}).get("text", "") for r in requests
	)
	assert "Empty Job" in full_text
	assert "No results" in full_text


def test_invalid_template_raises():
	from docs_formatter import format_rows_to_docs_requests

	with pytest.raises(ValueError, match="format_template"):
		format_rows_to_docs_requests(rows=[], format_template="bogus", title="x")

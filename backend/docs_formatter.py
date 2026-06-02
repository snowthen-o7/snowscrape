"""Pure functions for converting scrape rows into Google Docs batchUpdate requests.

Each format_template emits a list of dicts matching the Docs API request schema:
https://developers.google.com/docs/api/reference/rest/v1/documents/request
"""
from typing import Dict, List

VALID_TEMPLATES = {"structured_log", "compact_list", "narrative"}


def _insert_text(text: str, index: int) -> dict:
	return {"insertText": {"location": {"index": index}, "text": text}}


def _heading_style(start: int, end: int, level: str) -> dict:
	return {
		"updateParagraphStyle": {
			"range": {"startIndex": start, "endIndex": end},
			"paragraphStyle": {"namedStyleType": level},
			"fields": "namedStyleType",
		}
	}


def format_rows_to_docs_requests(
	rows: List[Dict],
	format_template: str,
	title: str,
) -> List[dict]:
	if format_template not in VALID_TEMPLATES:
		raise ValueError(f"format_template must be one of {sorted(VALID_TEMPLATES)}")

	if format_template == "structured_log":
		return _build_structured_log(rows, title)
	if format_template == "compact_list":
		return _build_compact_list(rows, title)
	return _build_narrative(rows, title)


def _build_structured_log(rows: List[Dict], title: str) -> List[dict]:
	requests: List[dict] = []
	index = 1
	text = f"{title}\n"
	requests.append(_insert_text(text, index))
	title_end = index + len(text)
	requests.append(_heading_style(index, title_end - 1, "TITLE"))
	index = title_end

	if not rows:
		body = "No results found.\n"
		requests.append(_insert_text(body, index))
		return requests

	for row in rows:
		row_title = str(row.get("title") or row.get("url") or "(untitled)")
		heading_text = f"{row_title}\n"
		requests.append(_insert_text(heading_text, index))
		heading_end = index + len(heading_text)
		requests.append(_heading_style(index, heading_end - 1, "HEADING_2"))
		index = heading_end

		field_lines: List[str] = []
		for key, value in row.items():
			if key in ("title",):
				continue
			field_lines.append(f"{key}: {value}")
		block = "\n".join(field_lines) + "\n\n"
		requests.append(_insert_text(block, index))
		index += len(block)

	return requests


def _build_compact_list(rows: List[Dict], title: str) -> List[dict]:
	requests: List[dict] = []
	index = 1
	header = f"{title}\n"
	requests.append(_insert_text(header, index))
	requests.append(_heading_style(index, index + len(header) - 1, "TITLE"))
	index += len(header)

	if not rows:
		text = "No results found.\n"
		requests.append(_insert_text(text, index))
		return requests

	body_lines: List[str] = []
	for row in rows:
		label = row.get("title") or row.get("url") or "(untitled)"
		body_lines.append(f"• {label}")
	text = "\n".join(body_lines) + "\n"
	requests.append(_insert_text(text, index))
	return requests


def _build_narrative(rows: List[Dict], title: str) -> List[dict]:
	requests: List[dict] = []
	index = 1
	header = f"{title}\n"
	requests.append(_insert_text(header, index))
	requests.append(_heading_style(index, index + len(header) - 1, "TITLE"))
	index += len(header)

	if not rows:
		text = "No results found.\n"
		requests.append(_insert_text(text, index))
		return requests

	paragraphs: List[str] = []
	for row in rows:
		body = row.get("body") or row.get("text") or row.get("content") or ""
		if body:
			paragraphs.append(str(body))
	text = "\n\n".join(paragraphs) + "\n"
	requests.append(_insert_text(text, index))
	return requests

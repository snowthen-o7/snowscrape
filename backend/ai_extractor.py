"""
AI-Powered Data Extraction using Anthropic Claude API.

Provides two main capabilities:
1. extract_with_ai() - Natural language data extraction from page content
2. suggest_queries() - AI-suggested XPath/CSS/regex selectors for a page
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

import anthropic

from logger import get_logger

logger = get_logger(__name__)

# Lazy-initialized singleton client
_anthropic_client = None

# Model to use for extraction (cost-effective, fast enough for Lambda)
EXTRACTION_MODEL = "claude-sonnet-4-20250514"

# Maximum content length to send to the API (chars)
MAX_CONTENT_LENGTH = 50000


def _get_client():
    """Lazy-initialize and return the Anthropic client singleton."""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is required for AI extraction. "
                "Set it via: npx sst secret set AnthropicApiKey <key>"
            )
        # `anthropic` is imported at module scope so tests can patch
        # `ai_extractor.anthropic`; only client construction stays lazy
        # (it needs the API key, absent at import time).
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def _truncate_content(content: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """Truncate content to max_length, preferring to break at paragraph boundaries."""
    if len(content) <= max_length:
        return content
    # Try to break at a paragraph boundary
    truncated = content[:max_length]
    last_newline = truncated.rfind('\n\n')
    if last_newline > max_length * 0.7:
        truncated = truncated[:last_newline]
    return truncated + "\n\n[Content truncated...]"


def _parse_json_response(text: str) -> Any:
    """Parse JSON from Claude's response, with fallback for markdown code blocks."""
    text = text.strip()

    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON object/array boundaries
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start_idx = text.find(start_char)
        end_idx = text.rfind(end_char)
        if start_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(text[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                pass

    logger.warning("Could not parse JSON from AI response", response_preview=text[:200])
    return {"raw_response": text}


def extract_with_ai(
    content: str,
    description: str,
    content_type: str = 'markdown',
) -> Dict[str, Any]:
    """
    Extract structured data from page content using natural language description.

    Args:
        content: Page content (markdown preferred, HTML as fallback)
        description: Natural language description of what to extract
            e.g. "Extract the product name, price, rating, and number of reviews"
        content_type: Type of content ('markdown' or 'html')

    Returns:
        Dictionary with:
            - fields: dict of extracted key-value pairs
            - model: model used
            - usage: { input_tokens, output_tokens }
    """
    client = _get_client()
    truncated_content = _truncate_content(content)

    system_prompt = (
        "You are a precise data extraction assistant. Given page content and a description "
        "of what to extract, return ONLY a valid JSON object with the extracted data.\n\n"
        "Rules:\n"
        "- Return a JSON object where keys are descriptive field names\n"
        "- Use snake_case for field names\n"
        "- If a value is not found, use null\n"
        "- For lists of items, return an array of objects\n"
        "- For prices, return as numbers (no currency symbols)\n"
        "- For dates, use ISO 8601 format\n"
        "- Do NOT include any explanation, markdown, or text outside the JSON\n"
        "- Return ONLY the JSON object, nothing else"
    )

    user_message = (
        f"Extract the following from this {content_type} content:\n\n"
        f"**What to extract:** {description}\n\n"
        f"**Page content:**\n{truncated_content}"
    )

    logger.info("Calling AI extraction",
                description=description[:100],
                content_length=len(truncated_content),
                content_type=content_type)

    try:
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = response.content[0].text
        fields = _parse_json_response(response_text)

        usage = {
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
        }

        logger.info("AI extraction completed",
                     field_count=len(fields) if isinstance(fields, dict) else 1,
                     input_tokens=usage['input_tokens'],
                     output_tokens=usage['output_tokens'])

        return {
            'fields': fields,
            'model': EXTRACTION_MODEL,
            'usage': usage,
        }

    except Exception as e:
        logger.error("AI extraction failed", error=str(e))
        raise


def suggest_queries(
    content: str,
    description: str,
    content_type: str = 'markdown',
) -> List[Dict[str, Any]]:
    """
    Suggest XPath/CSS/regex selectors for extracting data from a page.

    Args:
        content: Page content (markdown or HTML)
        description: Natural language description of what data to extract
        content_type: Type of content ('markdown' or 'html')

    Returns:
        List of suggestion dicts, each with:
            - name: field name
            - type: query type ('xpath', 'css', 'regex', 'ai')
            - query: the selector/expression
            - description: what this field extracts
            - sample_value: example value from the page
    """
    client = _get_client()
    truncated_content = _truncate_content(content)

    system_prompt = (
        "You are a web scraping expert. Given page content and a description of what to extract, "
        "suggest the best selectors (XPath, CSS, or regex) for each data field.\n\n"
        "Rules:\n"
        "- Return a JSON array of selector objects\n"
        "- Each object has: name, type, query, description, sample_value\n"
        "- type must be one of: 'xpath', 'css', 'regex', 'ai'\n"
        "- Prefer XPath for structured HTML data\n"
        "- Use regex for data embedded in text or attributes\n"
        "- Use 'ai' type (with the description as the query) when the data is too complex "
        "for simple selectors\n"
        "- Include a sample_value showing what the selector would extract\n"
        "- Return 3-8 suggestions\n"
        "- Return ONLY the JSON array, nothing else"
    )

    user_message = (
        f"Suggest selectors for extracting this data from the page:\n\n"
        f"**What to extract:** {description}\n\n"
        f"**Page content ({content_type}):**\n{truncated_content}"
    )

    logger.info("Calling AI for query suggestions",
                description=description[:100],
                content_length=len(truncated_content))

    try:
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = response.content[0].text
        suggestions = _parse_json_response(response_text)

        if not isinstance(suggestions, list):
            suggestions = [suggestions] if isinstance(suggestions, dict) else []

        logger.info("AI query suggestions completed",
                     suggestion_count=len(suggestions))

        return suggestions

    except Exception as e:
        logger.error("AI query suggestion failed", error=str(e))
        raise

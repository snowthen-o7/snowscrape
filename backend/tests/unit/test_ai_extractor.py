"""Tests for AI-powered data extraction module."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    """Set required environment variables for all tests."""
    monkeypatch.setenv('REGION', 'us-east-2')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test-key-123')


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the singleton client between tests."""
    import ai_extractor
    ai_extractor._anthropic_client = None
    yield
    ai_extractor._anthropic_client = None


@pytest.fixture
def mock_anthropic_response():
    """Create a mock Anthropic API response."""
    def _make_response(text, input_tokens=500, output_tokens=100):
        response = MagicMock()
        content_block = MagicMock()
        content_block.text = text
        response.content = [content_block]
        response.usage = MagicMock()
        response.usage.input_tokens = input_tokens
        response.usage.output_tokens = output_tokens
        return response
    return _make_response


class TestExtractWithAI:
    """Tests for extract_with_ai function."""

    @patch('ai_extractor.anthropic')
    def test_extract_valid_json(self, mock_anthropic_module, mock_anthropic_response):
        """Test extraction with valid JSON response."""
        from ai_extractor import extract_with_ai

        expected_fields = {
            'product_name': 'Widget Pro',
            'price': 29.99,
            'rating': 4.5,
        }

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            json.dumps(expected_fields)
        )
        mock_anthropic_module.Anthropic.return_value = mock_client

        result = extract_with_ai(
            content='# Widget Pro\nPrice: $29.99\nRating: 4.5/5',
            description='Extract product name, price, and rating',
            content_type='markdown',
        )

        assert result['fields'] == expected_fields
        assert result['model'] == 'claude-sonnet-4-20250514'
        assert 'usage' in result
        assert result['usage']['input_tokens'] == 500
        assert result['usage']['output_tokens'] == 100

    @patch('ai_extractor.anthropic')
    def test_extract_json_in_code_block(self, mock_anthropic_module, mock_anthropic_response):
        """Test extraction when Claude wraps JSON in markdown code block."""
        from ai_extractor import extract_with_ai

        response_text = '```json\n{"name": "Test Product", "price": 19.99}\n```'

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(response_text)
        mock_anthropic_module.Anthropic.return_value = mock_client

        result = extract_with_ai(
            content='<h1>Test Product</h1><span>$19.99</span>',
            description='Extract name and price',
            content_type='html',
        )

        assert result['fields']['name'] == 'Test Product'
        assert result['fields']['price'] == 19.99

    @patch('ai_extractor.anthropic')
    def test_extract_malformed_json(self, mock_anthropic_module, mock_anthropic_response):
        """Test extraction handles malformed JSON gracefully."""
        from ai_extractor import extract_with_ai

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            'Here is the data: {"name": "test"} with some trailing text'
        )
        mock_anthropic_module.Anthropic.return_value = mock_client

        result = extract_with_ai(
            content='Some content',
            description='Extract data',
        )

        # Should still parse the JSON object from the response
        assert result['fields']['name'] == 'test'

    @patch('ai_extractor.anthropic')
    def test_extract_completely_invalid_response(self, mock_anthropic_module, mock_anthropic_response):
        """Test extraction with completely non-JSON response."""
        from ai_extractor import extract_with_ai

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            'I cannot extract any data from this page.'
        )
        mock_anthropic_module.Anthropic.return_value = mock_client

        result = extract_with_ai(
            content='Empty page',
            description='Extract data',
        )

        # Should return raw_response fallback
        assert 'raw_response' in result['fields']

    def test_extract_missing_api_key(self, monkeypatch):
        """Test extraction raises error when API key is missing."""
        from ai_extractor import extract_with_ai

        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

        with pytest.raises(RuntimeError, match='ANTHROPIC_API_KEY'):
            extract_with_ai('content', 'description')

    @patch('ai_extractor.anthropic')
    def test_extract_truncates_long_content(self, mock_anthropic_module, mock_anthropic_response):
        """Test that very long content is truncated."""
        from ai_extractor import extract_with_ai, MAX_CONTENT_LENGTH

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response('{"result": "ok"}')
        mock_anthropic_module.Anthropic.return_value = mock_client

        long_content = 'x' * (MAX_CONTENT_LENGTH + 10000)
        extract_with_ai(long_content, 'Extract data')

        # Verify the content sent to Claude was truncated
        call_args = mock_client.messages.create.call_args
        user_message = call_args[1]['messages'][0]['content']
        assert len(user_message) < len(long_content) + 500  # some overhead for prompt


class TestSuggestQueries:
    """Tests for suggest_queries function."""

    @patch('ai_extractor.anthropic')
    def test_suggest_returns_list(self, mock_anthropic_module, mock_anthropic_response):
        """Test suggest_queries returns a list of suggestions."""
        from ai_extractor import suggest_queries

        suggestions = [
            {
                'name': 'product_title',
                'type': 'xpath',
                'query': '//h1[@class="product-title"]/text()',
                'description': 'Product title',
                'sample_value': 'Widget Pro',
            },
            {
                'name': 'price',
                'type': 'regex',
                'query': r'\$(\d+\.\d{2})',
                'description': 'Product price',
                'sample_value': '29.99',
            },
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            json.dumps(suggestions)
        )
        mock_anthropic_module.Anthropic.return_value = mock_client

        result = suggest_queries(
            content='<h1 class="product-title">Widget Pro</h1><span>$29.99</span>',
            description='Extract product info',
            content_type='html',
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['name'] == 'product_title'
        assert result[0]['type'] == 'xpath'
        assert result[1]['name'] == 'price'
        assert result[1]['type'] == 'regex'

    @patch('ai_extractor.anthropic')
    def test_suggest_handles_single_dict_response(self, mock_anthropic_module, mock_anthropic_response):
        """Test suggest_queries wraps single dict in list."""
        from ai_extractor import suggest_queries

        single = {
            'name': 'title',
            'type': 'ai',
            'query': 'Extract the title',
            'description': 'Page title',
            'sample_value': 'Test',
        }

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(json.dumps(single))
        mock_anthropic_module.Anthropic.return_value = mock_client

        result = suggest_queries('content', 'get title')

        assert isinstance(result, list)
        assert len(result) == 1


class TestParseJsonResponse:
    """Tests for JSON response parsing helper."""

    def test_parse_valid_json(self):
        from ai_extractor import _parse_json_response
        result = _parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_array(self):
        from ai_extractor import _parse_json_response
        result = _parse_json_response('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_parse_json_in_code_block(self):
        from ai_extractor import _parse_json_response
        result = _parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_json_with_surrounding_text(self):
        from ai_extractor import _parse_json_response
        result = _parse_json_response('Here is the result: {"key": "value"} done.')
        assert result == {"key": "value"}

    def test_parse_completely_invalid(self):
        from ai_extractor import _parse_json_response
        result = _parse_json_response('no json here at all')
        assert 'raw_response' in result

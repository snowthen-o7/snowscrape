"""Tests for Firecrawl-based tiered scraping (Tier 3 & 4)."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

import requests


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    """Set required environment variables for all tests."""
    monkeypatch.setenv('REGION', 'us-east-2')
    monkeypatch.setenv('FIRECRAWL_API_KEY', 'fc-test-key-123')


@pytest.fixture
def firecrawl_success_response():
    """Standard successful Firecrawl API response."""
    return {
        'success': True,
        'data': {
            'markdown': '# Test Page\n\nThis is a test product page.\n\n**Price:** $29.99',
            'html': '<html><head><title>Test Page</title></head><body>'
                    '<h1>Test Page</h1><p>This is a test product page.</p>'
                    '<div class="price">$29.99</div></body></html>',
            'metadata': {
                'title': 'Test Page',
                'statusCode': 200,
                'sourceURL': 'https://example.com/product',
            },
        },
    }


@pytest.fixture
def firecrawl_blocked_response():
    """Firecrawl response containing blocking indicators."""
    return {
        'success': True,
        'data': {
            'markdown': 'Access denied',
            'html': '<html><body>Access denied</body></html>',
            'metadata': {
                'title': '',
                'statusCode': 403,
                'sourceURL': 'https://example.com/blocked',
            },
        },
    }


class TestFirecrawlTier3:
    """Tests for Tier 3 (Firecrawl Scrape)."""

    @patch('tiered_scraper.requests.post')
    @patch('tiered_scraper.validate_scrape_url')
    def test_tier3_success(self, mock_validate, mock_post, firecrawl_success_response):
        """Test successful Tier 3 Firecrawl scrape."""
        from tiered_scraper import scrape_tier_3

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = firecrawl_success_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = scrape_tier_3('https://example.com/product')

        assert result['tier_used'] == 3
        assert result['tier_name'] == 'Firecrawl Scrape'
        assert result['js_rendered'] is True
        assert result['markdown'] == firecrawl_success_response['data']['markdown']
        assert result['firecrawl_metadata'] == firecrawl_success_response['data']['metadata']
        assert result['cost'] == 0.01
        assert result['soup'] is not None
        assert result['content'] is not None

        # Verify Firecrawl API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://api.firecrawl.dev/v1/scrape'
        assert call_args[1]['headers']['Authorization'] == 'Bearer fc-test-key-123'

    @patch('tiered_scraper.requests.post')
    @patch('tiered_scraper.validate_scrape_url')
    def test_tier3_blocking_detected(self, mock_validate, mock_post, firecrawl_blocked_response):
        """Test Tier 3 detects blocking in Firecrawl response."""
        from tiered_scraper import scrape_tier_3, BlockingDetectionError

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = firecrawl_blocked_response
        mock_response.raise_for_status = MagicMock()
        # detect_blocking checks response.status_code
        mock_response.text = firecrawl_blocked_response['data']['html']
        mock_post.return_value = mock_response

        with pytest.raises(BlockingDetectionError):
            scrape_tier_3('https://example.com/blocked')

    @patch('tiered_scraper.requests.post')
    @patch('tiered_scraper.validate_scrape_url')
    def test_tier3_firecrawl_failure(self, mock_validate, mock_post):
        """Test Tier 3 handles Firecrawl API failure."""
        from tiered_scraper import scrape_tier_3

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': False,
            'error': 'Rate limit exceeded',
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match='Firecrawl scrape failed'):
            scrape_tier_3('https://example.com')

    @patch('tiered_scraper.requests.post')
    @patch('tiered_scraper.validate_scrape_url')
    def test_tier3_network_error(self, mock_validate, mock_post):
        """Test Tier 3 handles network errors."""
        from tiered_scraper import scrape_tier_3

        mock_post.side_effect = requests.exceptions.ConnectionError('Connection refused')

        with pytest.raises(requests.exceptions.ConnectionError):
            scrape_tier_3('https://example.com')

    @patch('tiered_scraper.validate_scrape_url')
    def test_tier3_fallback_to_browserless(self, mock_validate, monkeypatch):
        """Test Tier 3 falls back to Browserless when FIRECRAWL_API_KEY not set."""
        from tiered_scraper import scrape_tier_3

        monkeypatch.delenv('FIRECRAWL_API_KEY', raising=False)
        monkeypatch.setenv('JS_RENDERER_URL', '')

        with pytest.raises(RuntimeError, match='FIRECRAWL_API_KEY or JS_RENDERER_URL'):
            scrape_tier_3('https://example.com')

    @patch('tiered_scraper.requests.post')
    @patch('tiered_scraper.validate_scrape_url')
    def test_tier3_result_has_all_keys(self, mock_validate, mock_post, firecrawl_success_response):
        """Test Tier 3 result dict has all expected keys including markdown."""
        from tiered_scraper import scrape_tier_3

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = firecrawl_success_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = scrape_tier_3('https://example.com/product')

        expected_keys = {
            'html', 'content', 'text', 'soup', 'title',
            'status_code', 'headers', 'url', 'tier_used',
            'tier_name', 'cost', 'js_rendered',
            'markdown', 'firecrawl_metadata',
        }
        assert expected_keys.issubset(set(result.keys()))


class TestFirecrawlTier4:
    """Tests for Tier 4 (Firecrawl Anti-Bot)."""

    @patch('tiered_scraper.requests.post')
    @patch('tiered_scraper.validate_scrape_url')
    def test_tier4_success_with_wait_actions(self, mock_validate, mock_post, firecrawl_success_response):
        """Test successful Tier 4 scrape includes wait actions."""
        from tiered_scraper import scrape_tier_4

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = firecrawl_success_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = scrape_tier_4('https://example.com/protected')

        assert result['tier_used'] == 4
        assert result['tier_name'] == 'Firecrawl Anti-Bot'
        assert result['cost'] == 0.05
        assert result['markdown'] is not None

        # Verify wait actions were included in payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert 'actions' in payload
        assert payload['actions'][0]['type'] == 'wait'
        assert payload['actions'][0]['milliseconds'] == 3000
        assert payload['waitFor'] == 5000

    @patch('tiered_scraper.requests.post')
    @patch('tiered_scraper.validate_scrape_url')
    def test_tier4_higher_timeout(self, mock_validate, mock_post, firecrawl_success_response):
        """Test Tier 4 uses higher default timeout."""
        from tiered_scraper import scrape_tier_4

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = firecrawl_success_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = scrape_tier_4('https://example.com/protected', timeout=60)

        assert result['tier_used'] == 4
        # Verify timeout was passed
        call_args = mock_post.call_args
        assert call_args[1]['timeout'] == 60


class TestTierInfoUpdated:
    """Test TIER_INFO constants reflect Firecrawl integration."""

    def test_tier3_info(self):
        from tiered_scraper import TIER_INFO
        assert TIER_INFO[3]['name'] == 'Firecrawl Scrape'
        assert TIER_INFO[3]['cost_per_page'] == 0.01
        assert TIER_INFO[3]['avg_time_seconds'] == 8

    def test_tier4_info(self):
        from tiered_scraper import TIER_INFO
        assert TIER_INFO[4]['name'] == 'Firecrawl Anti-Bot'
        assert TIER_INFO[4]['cost_per_page'] == 0.05
        assert TIER_INFO[4]['avg_time_seconds'] == 15

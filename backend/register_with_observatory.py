#!/usr/bin/env python3
"""
Register Snowscrape with Snowglobe Observatory.

Run this script after deploying to register or update snowscrape's metadata
in the Observatory dashboard.

Usage:
    python register_with_observatory.py [--stage dev|prod]
"""

import argparse
import os
import sys
from logger import get_logger
from observatory_client import ObservatoryClient

logger = get_logger(__name__)

# Public-facing registration metadata, sourced from docs/INFRASTRUCTURE.md.
# Per stage; override with SNOWSCRAPE_PUBLIC_URL / SNOWSCRAPE_API_BASE_URL when a
# stack is recreated with new API Gateway IDs so the script never re-registers
# stale placeholder values in the Observatory dashboard.
REPOSITORY_URL = 'https://github.com/snowthen-o7/snowscrape'

DEFAULT_PUBLIC_URL = {
	'dev': 'http://localhost:3001',
	'prod': 'https://scrape.snowforge.dev',
}

DEFAULT_API_BASE_URL = {
	'dev': 'https://g5vmashyda.execute-api.us-east-2.amazonaws.com',
	'prod': 'https://2pg2gj4048.execute-api.us-east-2.amazonaws.com',
}


def _public_url(stage):
	"""Public site URL for the given stage (the SNOWSCRAPE_PUBLIC_URL env var wins)."""
	return os.environ.get('SNOWSCRAPE_PUBLIC_URL') or DEFAULT_PUBLIC_URL.get(stage, '')


def _api_base_url(stage):
	"""Backend API base URL for the given stage (the SNOWSCRAPE_API_BASE_URL env var wins).

	A trailing slash is stripped so `{api_base}/health` never becomes `//health`
	when an operator supplies SNOWSCRAPE_API_BASE_URL with a trailing slash.
	"""
	base = os.environ.get('SNOWSCRAPE_API_BASE_URL') or DEFAULT_API_BASE_URL.get(stage, '')
	return base.rstrip('/')


def register_snowscrape(stage='dev'):
	"""
	Register snowscrape with Observatory.

	Args:
		stage: Deployment stage (dev or prod)
	"""
	# Initialize Observatory client
	observatory = ObservatoryClient()

	if not observatory.enabled:
		logger.error("SNOWGLOBE_API_KEY environment variable is not set")
		logger.error("Please set the following environment variables: SNOWGLOBE_API_KEY, SNOWGLOBE_URL (optional), SNOWGLOBE_SITE_ID (optional)")
		sys.exit(1)

	logger.info("Registering Snowscrape with Observatory", stage=stage, url=observatory.url, site_id=observatory.site_id)

	# Public-facing metadata for the Observatory dashboard (env override wins).
	domain = _public_url(stage)
	api_base = _api_base_url(stage)

	# Register with Observatory
	success = observatory.register(
		name=f'Snowscrape ({stage.upper()})',
		site_type='pipeline',
		platform='AWS Lambda',
		domain=domain,
		repository=REPOSITORY_URL,
		healthEndpoint=f'{api_base}/health',
		description='Web scraping pipeline for scheduled data extraction and processing',
		version='1.0.0',
		databases=['DynamoDB (SnowscrapeJobs, SnowscrapeUrls, SnowscrapeSessions)'],
		services=['S3 (snowscrape-results)', 'SQS (SnowscrapeJobQueue)', 'API Gateway', 'CloudWatch']
	)

	if success:
		logger.info("Successfully registered with Observatory", dashboard_url=f"{observatory.url}/observatory", site_url=f"{observatory.url}/observatory/{observatory.site_id}")
	else:
		logger.error("Failed to register with Observatory, check your API key and network connection")
		sys.exit(1)


def main():
	parser = argparse.ArgumentParser(
		description='Register Snowscrape with Snowglobe Observatory'
	)
	parser.add_argument(
		'--stage',
		choices=['dev', 'prod'],
		default='dev',
		help='Deployment stage (default: dev)'
	)

	args = parser.parse_args()
	register_snowscrape(args.stage)


if __name__ == '__main__':
	main()

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

	# Register with Observatory
	success = observatory.register(
		name=f'Snowscrape ({stage.upper()})',
		site_type='pipeline',
		platform='AWS Lambda',
		domain=f'https://api-snowscrape-{stage}.example.com',  # Update with your actual domain
		repository='https://github.com/alexdiaz/snowscrape',  # Update with your actual repo
		healthEndpoint=f'https://api-snowscrape-{stage}.example.com/health',  # Update
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

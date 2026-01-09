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
from observatory_client import ObservatoryClient


def register_snowscrape(stage='dev'):
	"""
	Register snowscrape with Observatory.

	Args:
		stage: Deployment stage (dev or prod)
	"""
	# Initialize Observatory client
	observatory = ObservatoryClient()

	if not observatory.enabled:
		print("❌ Error: SNOWGLOBE_API_KEY environment variable is not set")
		print("\nPlease set the following environment variables:")
		print("  export SNOWGLOBE_API_KEY='your-api-key'")
		print("  export SNOWGLOBE_URL='https://snowglobe.alexdiaz.me'  # optional")
		print("  export SNOWGLOBE_SITE_ID='snowscrape'  # optional")
		sys.exit(1)

	print(f"🚀 Registering Snowscrape ({stage}) with Observatory...")
	print(f"   URL: {observatory.url}")
	print(f"   Site ID: {observatory.site_id}")

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
		print("✅ Successfully registered with Observatory!")
		print(f"\n📊 View dashboard: {observatory.url}/observatory")
		print(f"🔍 View Snowscrape: {observatory.url}/observatory/{observatory.site_id}")
	else:
		print("❌ Failed to register with Observatory")
		print("   Check your API key and network connection")
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

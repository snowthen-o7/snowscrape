"""
Webhook delivery handler - SQS triggered Lambda function.
Handles async delivery of webhook events via HTTP POST with HMAC signatures.
"""

import boto3
import json
import os
import hashlib
import hmac
import time
import requests
from typing import Dict, List
from logger import get_logger

logger = get_logger(__name__)

dynamodb = boto3.resource('dynamodb')
webhooks_table = dynamodb.Table(os.environ['DYNAMODB_WEBHOOKS_TABLE'])
deliveries_table = dynamodb.Table(os.environ['DYNAMODB_WEBHOOK_DELIVERIES_TABLE'])


def webhook_delivery_handler(event, context):
    """
    Lambda handler for webhook delivery.
    Triggered by SQS messages from WebhookQueue.
    """
    failed_items = []

    for record in event['Records']:
        try:
            # Parse message body
            message = json.loads(record['body'])

            delivery_id = message['delivery_id']
            webhook_id = message['webhook_id']
            webhook_url = message['webhook_url']
            webhook_secret = message['webhook_secret']
            event_type = message['event_type']
            payload = message['payload']

            logger.info(
                "Processing webhook delivery",
                delivery_id=delivery_id,
                webhook_id=webhook_id,
                event_type=event_type
            )

            # Deliver the webhook
            success, status_code, response_body, error = deliver_webhook(
                webhook_url=webhook_url,
                webhook_secret=webhook_secret,
                event_type=event_type,
                delivery_id=delivery_id,
                payload=payload
            )

            # Log delivery to DynamoDB
            log_delivery(
                delivery_id=delivery_id,
                webhook_id=webhook_id,
                event_type=event_type,
                webhook_url=webhook_url,
                success=success,
                status_code=status_code,
                response_body=response_body,
                error=error
            )

            # Update webhook stats in Webhooks table
            update_webhook_stats(webhook_id, success)

            # If delivery failed, raise exception to trigger SQS retry
            if not success:
                logger.error(
                    "Webhook delivery failed",
                    delivery_id=delivery_id,
                    webhook_id=webhook_id,
                    status_code=status_code,
                    error=error
                )
                # Add to failed items for batch failure handling
                failed_items.append({
                    'itemIdentifier': record['messageId']
                })

        except Exception as e:
            logger.error("Error processing webhook delivery", error=str(e), record=record)
            # Add to failed items for batch failure handling
            failed_items.append({
                'itemIdentifier': record['messageId']
            })

    # Return batch item failures for SQS to retry
    return {
        'batchItemFailures': failed_items
    }


def deliver_webhook(webhook_url: str, webhook_secret: str, event_type: str,
                   delivery_id: str, payload: Dict) -> tuple:
    """
    Deliver webhook via HTTP POST with HMAC signature.

    Args:
        webhook_url: Target webhook URL
        webhook_secret: Secret for HMAC signature
        event_type: Event type (job.created, etc.)
        delivery_id: Unique delivery ID
        payload: Event payload

    Returns:
        Tuple of (success: bool, status_code: int, response_body: str, error: str)
    """
    try:
        # Prepare payload
        payload_json = json.dumps(payload)

        # Generate HMAC SHA256 signature
        signature = ''
        if webhook_secret:
            signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload_json.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'SnowScrape-Webhooks/1.0',
            'X-Snowscrape-Event': event_type,
            'X-Snowscrape-Delivery-ID': delivery_id,
            'X-Snowscrape-Timestamp': str(int(time.time()))
        }

        if signature:
            headers['X-Snowscrape-Signature'] = f'sha256={signature}'

        # Make HTTP POST request
        response = requests.post(
            webhook_url,
            data=payload_json,
            headers=headers,
            timeout=30  # 30 second timeout
        )

        # Check if successful (2xx status code)
        success = 200 <= response.status_code < 300

        logger.info(
            "Webhook delivered",
            delivery_id=delivery_id,
            webhook_url=webhook_url,
            status_code=response.status_code,
            success=success
        )

        # Truncate response body for logging (max 1000 chars)
        response_body = response.text[:1000] if response.text else ''

        return success, response.status_code, response_body, None

    except requests.exceptions.Timeout:
        logger.warning("Webhook delivery timeout", delivery_id=delivery_id, webhook_url=webhook_url)
        return False, 0, '', 'Request timeout'

    except requests.exceptions.RequestException as e:
        logger.error("Webhook delivery error", delivery_id=delivery_id, webhook_url=webhook_url, error=str(e))
        return False, 0, '', str(e)

    except Exception as e:
        logger.error("Unexpected error during webhook delivery", delivery_id=delivery_id, error=str(e))
        return False, 0, '', str(e)


def log_delivery(delivery_id: str, webhook_id: str, event_type: str, webhook_url: str,
                success: bool, status_code: int, response_body: str, error: str):
    """
    Log webhook delivery to DynamoDB.

    Args:
        delivery_id: Unique delivery ID
        webhook_id: Webhook ID
        event_type: Event type
        webhook_url: Target URL
        success: Whether delivery succeeded
        status_code: HTTP status code
        response_body: Response body (truncated)
        error: Error message if failed
    """
    try:
        timestamp = int(time.time())
        ttl = timestamp + (30 * 24 * 60 * 60)  # 30 days TTL

        deliveries_table.put_item(
            Item={
                'delivery_id': delivery_id,
                'webhook_id': webhook_id,
                'event_type': event_type,
                'webhook_url': webhook_url,
                'timestamp': timestamp,
                'success': success,
                'status_code': status_code,
                'response_body': response_body or '',
                'error': error or '',
                'ttl': ttl
            }
        )

        logger.info("Delivery logged to DynamoDB", delivery_id=delivery_id, success=success)

    except Exception as e:
        logger.error("Failed to log delivery", delivery_id=delivery_id, error=str(e))


def update_webhook_stats(webhook_id: str, success: bool):
    """
    Update webhook delivery statistics.

    Args:
        webhook_id: Webhook ID
        success: Whether delivery succeeded
    """
    try:
        # Increment total_deliveries and failed_deliveries (if failed)
        update_expression = 'SET total_deliveries = if_not_exists(total_deliveries, :zero) + :one'
        expression_values = {':one': 1, ':zero': 0}

        if not success:
            update_expression += ', failed_deliveries = if_not_exists(failed_deliveries, :zero) + :one'

        webhooks_table.update_item(
            Key={'webhook_id': webhook_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )

        logger.info("Webhook stats updated", webhook_id=webhook_id, success=success)

    except Exception as e:
        logger.error("Failed to update webhook stats", webhook_id=webhook_id, error=str(e))

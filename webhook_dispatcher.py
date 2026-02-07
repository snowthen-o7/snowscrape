"""
Webhook event dispatcher for sending webhook notifications to SQS.
Queries webhooks by event type and dispatches them to the webhook queue.
"""

import boto3
import json
import os
import uuid
from typing import Dict, List, Optional
from logger import get_logger

logger = get_logger(__name__)

dynamodb = boto3.resource('dynamodb')
sqs_client = boto3.client('sqs')

webhooks_table = dynamodb.Table(os.environ['DYNAMODB_WEBHOOKS_TABLE'])
webhook_queue_url = os.environ['SQS_WEBHOOK_QUEUE_URL']


class WebhookDispatcher:
    """Dispatches webhook events to SQS for async delivery."""

    @staticmethod
    def dispatch_event(event_type: str, job_id: str, user_id: str, payload: Dict) -> int:
        """
        Dispatch webhook event to all registered webhooks for this event type.

        Args:
            event_type: Type of event (job.created, job.completed, etc.)
            job_id: Job ID that triggered the event
            user_id: User ID who owns the job
            payload: Event payload to send to webhooks

        Returns:
            Number of webhooks triggered
        """
        try:
            # Query webhooks for this user (using GSI)
            response = webhooks_table.query(
                IndexName='UserIdIndex',
                KeyConditionExpression='user_id = :user_id',
                FilterExpression='active = :active',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':active': True
                }
            )

            webhooks = response.get('Items', [])
            logger.info("Found webhooks for user", user_id=user_id, count=len(webhooks))

            # Filter webhooks that are subscribed to this event type
            matching_webhooks = [
                webhook for webhook in webhooks
                if event_type in webhook.get('events', [])
                # Also match job-specific webhooks
                or (webhook.get('job_id') and webhook['job_id'] == job_id and event_type in webhook.get('events', []))
            ]

            if not matching_webhooks:
                logger.info("No webhooks subscribed to event", event_type=event_type, user_id=user_id)
                return 0

            # Send message to SQS for each webhook
            messages_sent = 0
            for webhook in matching_webhooks:
                delivery_id = str(uuid.uuid4())

                message = {
                    'delivery_id': delivery_id,
                    'webhook_id': webhook['webhook_id'],
                    'webhook_url': webhook['url'],
                    'webhook_secret': webhook.get('secret', ''),
                    'event_type': event_type,
                    'job_id': job_id,
                    'user_id': user_id,
                    'payload': payload
                }

                try:
                    sqs_client.send_message(
                        QueueUrl=webhook_queue_url,
                        MessageBody=json.dumps(message),
                        MessageGroupId=webhook['webhook_id'] if webhook_queue_url.endswith('.fifo') else None,
                        MessageDeduplicationId=delivery_id if webhook_queue_url.endswith('.fifo') else None
                    )
                    messages_sent += 1
                    logger.info(
                        "Webhook event dispatched to SQS",
                        webhook_id=webhook['webhook_id'],
                        event_type=event_type,
                        delivery_id=delivery_id
                    )
                except Exception as e:
                    logger.error(
                        "Failed to dispatch webhook to SQS",
                        webhook_id=webhook['webhook_id'],
                        error=str(e)
                    )

            logger.info(
                "Webhook dispatch completed",
                event_type=event_type,
                job_id=job_id,
                webhooks_triggered=messages_sent
            )
            return messages_sent

        except Exception as e:
            logger.error("Error dispatching webhook events", event_type=event_type, error=str(e))
            return 0

    @staticmethod
    def dispatch_job_created(job_id: str, user_id: str, job_data: Dict) -> int:
        """Dispatch job.created event."""
        payload = {
            'event': 'job.created',
            'job_id': job_id,
            'job_name': job_data.get('name'),
            'created_at': job_data.get('created_at'),
            'source': job_data.get('source'),
            'link_count': job_data.get('link_count', 0)
        }
        return WebhookDispatcher.dispatch_event('job.created', job_id, user_id, payload)

    @staticmethod
    def dispatch_job_started(job_id: str, user_id: str, job_data: Dict) -> int:
        """Dispatch job.started event."""
        payload = {
            'event': 'job.started',
            'job_id': job_id,
            'job_name': job_data.get('name'),
            'started_at': job_data.get('last_run'),
            'link_count': job_data.get('link_count', 0)
        }
        return WebhookDispatcher.dispatch_event('job.started', job_id, user_id, payload)

    @staticmethod
    def dispatch_job_completed(job_id: str, user_id: str, job_data: Dict, results_summary: Dict) -> int:
        """Dispatch job.completed event."""
        payload = {
            'event': 'job.completed',
            'job_id': job_id,
            'job_name': job_data.get('name'),
            'completed_at': job_data.get('last_run'),
            'results_s3_key': job_data.get('results_s3_key'),
            'summary': results_summary
        }
        return WebhookDispatcher.dispatch_event('job.completed', job_id, user_id, payload)

    @staticmethod
    def dispatch_job_failed(job_id: str, user_id: str, job_data: Dict, error: str) -> int:
        """Dispatch job.failed event."""
        payload = {
            'event': 'job.failed',
            'job_id': job_id,
            'job_name': job_data.get('name'),
            'failed_at': job_data.get('last_run'),
            'error': error
        }
        return WebhookDispatcher.dispatch_event('job.failed', job_id, user_id, payload)

    @staticmethod
    def dispatch_job_cancelled(job_id: str, user_id: str, job_data: Dict) -> int:
        """Dispatch job.cancelled event."""
        payload = {
            'event': 'job.cancelled',
            'job_id': job_id,
            'job_name': job_data.get('name'),
            'cancelled_at': job_data.get('last_run')
        }
        return WebhookDispatcher.dispatch_event('job.cancelled', job_id, user_id, payload)

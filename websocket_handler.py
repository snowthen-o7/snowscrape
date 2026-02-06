"""
WebSocket Handler for Real-time Updates
Handles WebSocket connections via AWS API Gateway WebSocket API
"""

import boto3
import json
import os
import time
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from connection_pool import get_table
from logger import get_logger
from utils import validate_clerk_token

logger = get_logger(__name__)

# DynamoDB table for WebSocket connections
CONNECTIONS_TABLE = os.environ.get('DYNAMODB_CONNECTIONS_TABLE', 'SnowscrapeConnections')
connections_table = None

def get_connections_table():
    """Get or create connection to the connections table."""
    global connections_table
    if connections_table is None:
        connections_table = get_table(CONNECTIONS_TABLE)
    return connections_table


def get_api_gateway_client(event):
    """
    Create API Gateway Management API client for sending messages.
    """
    domain = event.get('requestContext', {}).get('domainName')
    stage = event.get('requestContext', {}).get('stage')

    if not domain or not stage:
        raise ValueError("Missing domainName or stage in request context")

    endpoint_url = f"https://{domain}/{stage}"
    return boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)


def ws_connect_handler(event, context):
    """
    Handle WebSocket $connect route.
    Accepts the connection without requiring auth in the query string.
    Authentication is performed via the first message after connection opens.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')

    if not connection_id:
        logger.error("No connection ID in event")
        return {'statusCode': 400, 'body': 'Missing connection ID'}

    try:
        # Store the connection in a pending (unauthenticated) state.
        # The client must send an 'authenticate' action as its first message.
        table = get_connections_table()
        table.put_item(Item={
            'connection_id': connection_id,
            'user_id': '__unauthenticated__',
            'authenticated': False,
            'connected_at': int(time.time()),
            'subscriptions': [],
            'ttl': int(time.time()) + 300  # Short 5-minute TTL until authenticated
        })

        logger.info(f"[WS Connect] Connection {connection_id} established (pending auth)")
        return {'statusCode': 200, 'body': 'Connected'}

    except Exception as e:
        logger.error(f"[WS Connect] Error storing connection: {str(e)}")
        return {'statusCode': 500, 'body': f'Connection error: {str(e)}'}


def ws_disconnect_handler(event, context):
    """
    Handle WebSocket $disconnect route.
    Removes connection from storage.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')

    if not connection_id:
        logger.error("No connection ID in disconnect event")
        return {'statusCode': 400, 'body': 'Missing connection ID'}

    try:
        table = get_connections_table()
        table.delete_item(Key={'connection_id': connection_id})
        logger.info(f"[WS Disconnect] Connection {connection_id} removed")
        return {'statusCode': 200, 'body': 'Disconnected'}

    except Exception as e:
        logger.error(f"[WS Disconnect] Error removing connection: {str(e)}")
        return {'statusCode': 500, 'body': 'Error disconnecting'}


def is_connection_authenticated(connection_id):
    """Check if a connection has been authenticated."""
    try:
        table = get_connections_table()
        response = table.get_item(Key={'connection_id': connection_id})
        item = response.get('Item')
        if not item:
            return False
        return item.get('authenticated', False)
    except Exception as e:
        logger.error(f"[WS Auth Check] Error checking auth for {connection_id}: {str(e)}")
        return False


def ws_default_handler(event, context):
    """
    Handle WebSocket $default route (all messages).
    Requires authentication before processing any actions other than 'authenticate'.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')

    if not connection_id:
        return {'statusCode': 400, 'body': 'Missing connection ID'}

    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        message_type = body.get('type')

        # Handle the 'authenticate' action (sent as first message after connect)
        if action == 'authenticate':
            return handle_authenticate(connection_id, body, event)

        # For all other actions, require authentication first
        if not is_connection_authenticated(connection_id):
            logger.warning(f"[WS Default] Unauthenticated message from {connection_id}")
            return send_to_connection(event, connection_id, {
                'type': 'auth_error',
                'message': 'Not authenticated. Send an authenticate action first.'
            })

        # Handle re-authentication (token refresh) for already-authenticated connections
        if message_type == 'auth':
            return handle_auth(connection_id, body, event)

        elif message_type == 'subscribe':
            return handle_subscribe(connection_id, body)

        elif message_type == 'unsubscribe':
            return handle_unsubscribe(connection_id, body)

        elif message_type == 'ping':
            # Heartbeat - just respond with pong
            return send_to_connection(event, connection_id, {'type': 'pong'})

        else:
            logger.warning(f"[WS Default] Unknown message type: {message_type}")
            return send_to_connection(event, connection_id, {
                'type': 'error',
                'message': f'Unknown message type: {message_type}'
            })

    except json.JSONDecodeError:
        logger.error(f"[WS Default] Invalid JSON from {connection_id}")
        return {'statusCode': 400, 'body': 'Invalid JSON'}

    except Exception as e:
        logger.error(f"[WS Default] Error processing message: {str(e)}")
        return {'statusCode': 500, 'body': 'Internal error'}


def handle_authenticate(connection_id, body, event):
    """
    Handle initial authentication after WebSocket connection.
    This is sent as the first message from the client, replacing the old
    query-string token approach to avoid token exposure in logs and browser history.
    """
    token = body.get('token')

    if not token:
        return send_to_connection(event, connection_id, {
            'type': 'auth_error',
            'message': 'No token provided'
        })

    try:
        decoded_token = validate_clerk_token(token)
        user_id = decoded_token.get('sub')

        if not user_id:
            return send_to_connection(event, connection_id, {
                'type': 'auth_error',
                'message': 'Invalid token: no user ID'
            })

        # Upgrade the connection from pending to authenticated
        table = get_connections_table()
        table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='SET user_id = :uid, authenticated = :auth, ttl = :ttl',
            ExpressionAttributeValues={
                ':uid': user_id,
                ':auth': True,
                ':ttl': int(time.time()) + 86400  # Extend TTL to 24 hours once authenticated
            }
        )

        logger.info(f"[WS Authenticate] Connection {connection_id} authenticated as user {user_id}")
        return send_to_connection(event, connection_id, {
            'type': 'auth_success',
            'user_id': user_id
        })

    except Exception as e:
        logger.error(f"[WS Authenticate] Error: {str(e)}")
        return send_to_connection(event, connection_id, {
            'type': 'auth_error',
            'message': str(e)
        })


def handle_auth(connection_id, body, event):
    """Handle authentication message (token refresh)."""
    token = body.get('token')

    if not token:
        return send_to_connection(event, connection_id, {
            'type': 'auth_error',
            'message': 'No token provided'
        })

    try:
        decoded_token = validate_clerk_token(token)
        user_id = decoded_token.get('sub')

        # Update connection with new user ID (in case of token refresh)
        table = get_connections_table()
        table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='SET user_id = :uid, ttl = :ttl',
            ExpressionAttributeValues={
                ':uid': user_id,
                ':ttl': int(time.time()) + 86400
            }
        )

        return send_to_connection(event, connection_id, {
            'type': 'auth_success',
            'user_id': user_id
        })

    except Exception as e:
        logger.error(f"[WS Auth] Error: {str(e)}")
        return send_to_connection(event, connection_id, {
            'type': 'auth_error',
            'message': str(e)
        })


def handle_subscribe(connection_id, body):
    """Handle subscription to a channel."""
    channel = body.get('channel')

    if not channel:
        return {'statusCode': 400, 'body': 'No channel specified'}

    try:
        table = get_connections_table()

        # Add channel to subscriptions using DynamoDB SET
        table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='ADD subscriptions :channel',
            ExpressionAttributeValues={':channel': {channel}}
        )

        logger.info(f"[WS Subscribe] {connection_id} subscribed to {channel}")
        return {'statusCode': 200, 'body': f'Subscribed to {channel}'}

    except Exception as e:
        logger.error(f"[WS Subscribe] Error: {str(e)}")
        return {'statusCode': 500, 'body': 'Subscription error'}


def handle_unsubscribe(connection_id, body):
    """Handle unsubscription from a channel."""
    channel = body.get('channel')

    if not channel:
        return {'statusCode': 400, 'body': 'No channel specified'}

    try:
        table = get_connections_table()

        # Remove channel from subscriptions
        table.update_item(
            Key={'connection_id': connection_id},
            UpdateExpression='DELETE subscriptions :channel',
            ExpressionAttributeValues={':channel': {channel}}
        )

        logger.info(f"[WS Unsubscribe] {connection_id} unsubscribed from {channel}")
        return {'statusCode': 200, 'body': f'Unsubscribed from {channel}'}

    except Exception as e:
        logger.error(f"[WS Unsubscribe] Error: {str(e)}")
        return {'statusCode': 500, 'body': 'Unsubscription error'}


def send_to_connection(event, connection_id, data):
    """Send data to a specific WebSocket connection."""
    try:
        client = get_api_gateway_client(event)
        client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(data).encode('utf-8')
        )
        return {'statusCode': 200, 'body': 'Message sent'}

    except client.exceptions.GoneException:
        # Connection is stale, remove it
        logger.info(f"[WS Send] Connection {connection_id} is gone, removing")
        try:
            table = get_connections_table()
            table.delete_item(Key={'connection_id': connection_id})
        except:
            pass
        return {'statusCode': 410, 'body': 'Connection gone'}

    except Exception as e:
        logger.error(f"[WS Send] Error sending to {connection_id}: {str(e)}")
        return {'statusCode': 500, 'body': 'Send error'}


def broadcast_to_channel(domain, stage, channel, data, exclude_connection=None):
    """
    Broadcast a message to all connections subscribed to a channel.

    Args:
        domain: API Gateway domain name
        stage: API Gateway stage
        channel: The channel to broadcast to (e.g., 'jobs:all', 'job:123')
        data: The data to send
        exclude_connection: Optional connection ID to exclude from broadcast
    """
    endpoint_url = f"https://{domain}/{stage}"
    client = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)

    table = get_connections_table()

    # Scan for connections with this channel in their subscriptions
    # Note: For production at scale, consider using a GSI on subscriptions
    try:
        response = table.scan(
            FilterExpression='contains(subscriptions, :channel)',
            ExpressionAttributeValues={':channel': channel}
        )

        connections = response.get('Items', [])
        stale_connections = []

        for conn in connections:
            connection_id = conn['connection_id']

            if exclude_connection and connection_id == exclude_connection:
                continue

            try:
                client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(data).encode('utf-8')
                )
            except client.exceptions.GoneException:
                stale_connections.append(connection_id)
            except Exception as e:
                logger.error(f"[Broadcast] Error sending to {connection_id}: {str(e)}")

        # Clean up stale connections
        for conn_id in stale_connections:
            try:
                table.delete_item(Key={'connection_id': conn_id})
                logger.info(f"[Broadcast] Removed stale connection {conn_id}")
            except:
                pass

        logger.info(f"[Broadcast] Sent to {len(connections) - len(stale_connections)} connections on {channel}")

    except Exception as e:
        logger.error(f"[Broadcast] Error broadcasting to {channel}: {str(e)}")


def broadcast_to_user(domain, stage, user_id, data):
    """
    Broadcast a message to all connections for a specific user.

    Args:
        domain: API Gateway domain name
        stage: API Gateway stage
        user_id: The user ID to broadcast to
        data: The data to send
    """
    endpoint_url = f"https://{domain}/{stage}"
    client = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)

    table = get_connections_table()

    try:
        # Query connections for this user
        response = table.scan(
            FilterExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )

        connections = response.get('Items', [])
        stale_connections = []

        for conn in connections:
            connection_id = conn['connection_id']

            try:
                client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(data).encode('utf-8')
                )
            except client.exceptions.GoneException:
                stale_connections.append(connection_id)
            except Exception as e:
                logger.error(f"[Broadcast User] Error sending to {connection_id}: {str(e)}")

        # Clean up stale connections
        for conn_id in stale_connections:
            try:
                table.delete_item(Key={'connection_id': conn_id})
            except:
                pass

        logger.info(f"[Broadcast User] Sent to {len(connections) - len(stale_connections)} connections for user {user_id}")

    except Exception as e:
        logger.error(f"[Broadcast User] Error broadcasting to user {user_id}: {str(e)}")


# Utility function to be called from job processing to notify of status changes
def notify_job_status_change(job_id, user_id, status, job_data=None):
    """
    Notify connected clients about a job status change.
    Call this from job processing functions when status changes.

    Args:
        job_id: The job ID
        user_id: The user who owns the job
        status: The new job status
        job_data: Optional full job data to include
    """
    # Get WebSocket endpoint from environment
    ws_domain = os.environ.get('WS_API_DOMAIN')
    ws_stage = os.environ.get('WS_API_STAGE', 'dev')

    if not ws_domain:
        logger.debug("[Notify] WebSocket domain not configured, skipping notification")
        return

    message = {
        'type': 'job:status',
        'data': {
            'job_id': job_id,
            'status': status,
            **(job_data or {})
        }
    }

    # Broadcast to the specific job channel
    broadcast_to_channel(ws_domain, ws_stage, f'job:{job_id}', message)

    # Also broadcast to the 'jobs:all' channel
    broadcast_to_channel(ws_domain, ws_stage, 'jobs:all', message)

    # And broadcast to the specific user
    broadcast_to_user(ws_domain, ws_stage, user_id, message)

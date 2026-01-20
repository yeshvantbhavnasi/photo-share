"""
Rate Limiting and Abuse Detection Module

This module implements request rate limiting and abuse detection for the Photo Share application.
It tracks requests by IP address and user ID, enforces rate limits, and detects abuse patterns.
"""

import os
import time
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
rate_limit_table = dynamodb.Table(os.environ.get('RATE_LIMIT_TABLE', 'RateLimitTracking'))
abuse_table = dynamodb.Table(os.environ.get('ABUSE_TABLE', 'AbuseDetection'))

# Rate limit configuration (requests per minute)
RATE_LIMITS = {
    'global': int(os.environ.get('RATE_LIMIT_THRESHOLD', 100)),
    '/share': 10,     # Share link creation (10/min)
    '/edit': 5,       # AI edits are expensive (5/min)
    '/upload': 20,    # Photo uploads (20/min)
    '/albums': 50,    # Album listing (50/min)
    '/timeline': 50,  # Timeline queries (50/min)
}

# Severity thresholds
CRITICAL_THRESHOLD = int(os.environ.get('CRITICAL_THRESHOLD', 200))
NOTIFICATION_COOLDOWN_SECONDS = 900  # 15 minutes


def get_rate_limit(endpoint):
    """Get the rate limit for a specific endpoint.

    Args:
        endpoint: The API endpoint (e.g., '/share', '/edit')

    Returns:
        int: The rate limit (requests per minute) for this endpoint
    """
    # Match endpoint to configured limits
    for pattern, limit in RATE_LIMITS.items():
        if pattern == 'global':
            continue
        if endpoint.startswith(pattern):
            return limit

    # Return global limit as default
    return RATE_LIMITS['global']


def check_rate_limit(identifier, endpoint, window_seconds=60):
    """Check if the request is within rate limits.

    Args:
        identifier: User identifier (e.g., "IP#1.2.3.4" or "USER#abc123")
        endpoint: The API endpoint being accessed
        window_seconds: Time window for rate limiting (default: 60 seconds)

    Returns:
        dict: {
            'allowed': bool,
            'current_count': int,
            'limit': int,
            'window_start': float,
            'time_until_reset': float
        }
    """
    try:
        limit = get_rate_limit(endpoint)
        current_time = time.time()
        window_start = int(current_time / window_seconds) * window_seconds

        # Create request key: "ENDPOINT#/path#window_start"
        request_key = f"ENDPOINT#{endpoint}#{int(window_start)}"

        # Try to get existing rate limit entry
        try:
            response = rate_limit_table.get_item(
                Key={
                    'identifier': identifier,
                    'requestKey': request_key
                }
            )

            if 'Item' in response:
                item = response['Item']
                current_count = int(item.get('count', 0))

                # Check if we're over the limit
                if current_count >= limit:
                    time_until_reset = window_start + window_seconds - current_time
                    return {
                        'allowed': False,
                        'current_count': current_count,
                        'limit': limit,
                        'window_start': window_start,
                        'time_until_reset': time_until_reset,
                        'reason': 'rate_limit_exceeded'
                    }

        except Exception as get_error:
            print(f"Error getting rate limit entry: {get_error}")
            # If we can't read the entry, allow the request (fail open)
            return {
                'allowed': True,
                'current_count': 0,
                'limit': limit,
                'window_start': window_start,
                'time_until_reset': window_seconds
            }

        # Request is allowed
        return {
            'allowed': True,
            'current_count': response['Item'].get('count', 0) if 'Item' in response else 0,
            'limit': limit,
            'window_start': window_start,
            'time_until_reset': window_start + window_seconds - current_time
        }

    except Exception as e:
        print(f"Error in check_rate_limit: {e}")
        # On error, allow the request (fail open)
        return {
            'allowed': True,
            'current_count': 0,
            'limit': RATE_LIMITS['global'],
            'window_start': time.time(),
            'time_until_reset': 60,
            'error': str(e)
        }


def record_request(identifier, endpoint, metadata=None):
    """Record a request in the rate limit tracker.

    Args:
        identifier: User identifier (e.g., "IP#1.2.3.4" or "USER#abc123")
        endpoint: The API endpoint being accessed
        metadata: Optional dict with request metadata

    Returns:
        dict: {
            'recorded': bool,
            'count': int,
            'window_start': float
        }
    """
    try:
        window_seconds = 60
        current_time = time.time()
        window_start = int(current_time / window_seconds) * window_seconds

        # Create request key
        request_key = f"ENDPOINT#{endpoint}#{int(window_start)}"

        # Calculate TTL (expire 1 hour after window ends)
        ttl = int(window_start + window_seconds + 3600)

        # Increment counter atomically
        response = rate_limit_table.update_item(
            Key={
                'identifier': identifier,
                'requestKey': request_key
            },
            UpdateExpression='SET #count = if_not_exists(#count, :zero) + :inc, '
                           '#endpoint = :endpoint, '
                           '#windowStart = :windowStart, '
                           '#timestamp = :timestamp, '
                           '#ttl = :ttl',
            ExpressionAttributeNames={
                '#count': 'count',
                '#endpoint': 'endpoint',
                '#windowStart': 'windowStart',
                '#timestamp': 'timestamp',
                '#ttl': 'ttl'
            },
            ExpressionAttributeValues={
                ':zero': 0,
                ':inc': 1,
                ':endpoint': endpoint,
                ':windowStart': Decimal(str(window_start)),
                ':timestamp': datetime.utcnow().isoformat() + 'Z',
                ':ttl': ttl
            },
            ReturnValues='ALL_NEW'
        )

        new_count = int(response['Attributes']['count'])

        # Add metadata if provided
        if metadata:
            rate_limit_table.update_item(
                Key={
                    'identifier': identifier,
                    'requestKey': request_key
                },
                UpdateExpression='SET metadata = :metadata',
                ExpressionAttributeValues={
                    ':metadata': metadata
                }
            )

        return {
            'recorded': True,
            'count': new_count,
            'window_start': window_start
        }

    except Exception as e:
        print(f"Error recording request: {e}")
        return {
            'recorded': False,
            'count': 0,
            'window_start': 0,
            'error': str(e)
        }


def detect_abuse(identifier, request_count, endpoint):
    """Detect if the request pattern indicates abuse.

    Args:
        identifier: User identifier
        request_count: Number of requests in current window
        endpoint: The API endpoint

    Returns:
        dict: {
            'is_abuse': bool,
            'severity': str,  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
            'reason': str,
            'should_block': bool
        }
    """
    try:
        # Determine severity based on request count
        global_limit = RATE_LIMITS['global']

        if request_count < global_limit:
            return {
                'is_abuse': False,
                'severity': 'NONE',
                'reason': 'within_limits',
                'should_block': False
            }

        # Calculate severity
        if request_count >= 300:
            severity = 'CRITICAL'
            should_block = True
            reason = f'Extreme request rate: {request_count}/min (limit: {global_limit})'
        elif request_count >= CRITICAL_THRESHOLD:
            severity = 'HIGH'
            should_block = True
            reason = f'High request rate: {request_count}/min (limit: {global_limit})'
        elif request_count >= 150:
            severity = 'MEDIUM'
            should_block = False
            reason = f'Elevated request rate: {request_count}/min (limit: {global_limit})'
        else:
            severity = 'LOW'
            should_block = False
            reason = f'Slightly elevated request rate: {request_count}/min (limit: {global_limit})'

        # Check for expensive operation abuse
        endpoint_limit = get_rate_limit(endpoint)
        if request_count > endpoint_limit * 2:
            if severity in ['LOW', 'MEDIUM']:
                severity = 'HIGH'
                should_block = True
            reason += f' | Endpoint abuse: {endpoint} ({request_count}/min, limit: {endpoint_limit})'

        return {
            'is_abuse': True,
            'severity': severity,
            'reason': reason,
            'should_block': should_block,
            'request_count': request_count,
            'limit': global_limit
        }

    except Exception as e:
        print(f"Error detecting abuse: {e}")
        return {
            'is_abuse': False,
            'severity': 'NONE',
            'reason': 'detection_error',
            'should_block': False,
            'error': str(e)
        }


def should_send_notification(identifier, severity):
    """Check if we should send a notification for this abuse event.

    Implements cooldown to prevent notification spam.

    Args:
        identifier: User identifier
        severity: Abuse severity level

    Returns:
        dict: {
            'should_send': bool,
            'reason': str,
            'last_notification': str or None
        }
    """
    try:
        current_time = datetime.utcnow()
        cooldown_key = f"NOTIFICATION#{identifier}"

        # Check if we've sent a notification recently
        try:
            response = abuse_table.query(
                KeyConditionExpression='identifier = :identifier',
                ExpressionAttributeValues={
                    ':identifier': cooldown_key
                },
                ScanIndexForward=False,  # Get most recent first
                Limit=1
            )

            if response['Items']:
                last_notification_item = response['Items'][0]
                last_notification_time = datetime.fromisoformat(
                    last_notification_item['timestamp'].replace('Z', '+00:00')
                )

                time_since_last = (current_time - last_notification_time.replace(tzinfo=None)).total_seconds()

                if time_since_last < NOTIFICATION_COOLDOWN_SECONDS:
                    return {
                        'should_send': False,
                        'reason': f'cooldown_active ({int(NOTIFICATION_COOLDOWN_SECONDS - time_since_last)}s remaining)',
                        'last_notification': last_notification_item['timestamp']
                    }

        except Exception as query_error:
            print(f"Error checking notification cooldown: {query_error}")
            # If we can't check, allow notification (fail open)

        return {
            'should_send': True,
            'reason': 'cooldown_expired_or_first_notification',
            'last_notification': None
        }

    except Exception as e:
        print(f"Error in should_send_notification: {e}")
        return {
            'should_send': False,
            'reason': f'error: {str(e)}',
            'last_notification': None
        }


def record_abuse_event(identifier, abuse_info, endpoint):
    """Record an abuse event in the AbuseDetection table.

    Args:
        identifier: User identifier
        abuse_info: Dict with abuse detection info
        endpoint: The API endpoint

    Returns:
        dict: {'recorded': bool, 'event_id': str}
    """
    try:
        current_time = datetime.utcnow()
        timestamp = current_time.isoformat() + 'Z'

        # Calculate TTL (7 days)
        ttl = int((current_time + timedelta(days=7)).timestamp())

        # Record the abuse event
        abuse_table.put_item(
            Item={
                'identifier': identifier,
                'timestamp': timestamp,
                'abuseType': 'rate_limit_violation',
                'severity': abuse_info['severity'],
                'count': abuse_info.get('request_count', 0),
                'endpoint': endpoint,
                'reason': abuse_info.get('reason', ''),
                'shouldBlock': abuse_info.get('should_block', False),
                'ttl': ttl,
                'details': {
                    'limit': abuse_info.get('limit', 0),
                    'requestCount': abuse_info.get('request_count', 0)
                }
            }
        )

        # Also record notification cooldown entry
        cooldown_key = f"NOTIFICATION#{identifier}"
        abuse_table.put_item(
            Item={
                'identifier': cooldown_key,
                'timestamp': timestamp,
                'abuseType': 'notification_cooldown',
                'severity': abuse_info['severity'],
                'ttl': ttl
            }
        )

        return {
            'recorded': True,
            'event_id': f"{identifier}#{timestamp}"
        }

    except Exception as e:
        print(f"Error recording abuse event: {e}")
        return {
            'recorded': False,
            'event_id': None,
            'error': str(e)
        }


def publish_cloudwatch_metrics(identifier, abuse_info, endpoint):
    """Publish custom metrics to CloudWatch for monitoring.

    Args:
        identifier: User identifier
        abuse_info: Dict with abuse detection info
        endpoint: The API endpoint
    """
    try:
        cloudwatch = boto3.client('cloudwatch')

        metrics = [
            {
                'MetricName': 'RateLimitExceeded',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Application', 'Value': 'PhotoShare'},
                    {'Name': 'Endpoint', 'Value': endpoint},
                ]
            }
        ]

        if abuse_info.get('is_abuse'):
            metrics.append({
                'MetricName': 'AbuseDetected',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Application', 'Value': 'PhotoShare'},
                    {'Name': 'Severity', 'Value': abuse_info['severity']},
                    {'Name': 'Endpoint', 'Value': endpoint},
                ]
            })

        cloudwatch.put_metric_data(
            Namespace='PhotoShare/RateLimiting',
            MetricData=metrics
        )

    except Exception as e:
        print(f"Error publishing CloudWatch metrics: {e}")

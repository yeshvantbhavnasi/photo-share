"""
Notification Handler Module

This module sends email and SMS notifications for abuse detection events.
Uses AWS SES for email and SNS for SMS notifications.
"""

import os
import boto3
from datetime import datetime

# Initialize AWS clients
ses = boto3.client('ses')
sns = boto3.client('sns')
cloudwatch = boto3.client('cloudwatch')

# Configuration
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'bhavnasiyeshvant@gmail.com')
ADMIN_PHONE = os.environ.get('ADMIN_PHONE', '+19808337919')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')
CRITICAL_THRESHOLD = int(os.environ.get('CRITICAL_THRESHOLD', 200))


def format_identifier(identifier):
    """Format identifier for display (remove prefix).

    Args:
        identifier: Raw identifier (e.g., "IP#1.2.3.4" or "USER#abc123")

    Returns:
        str: Formatted identifier (e.g., "1.2.3.4" or "User abc123")
    """
    if identifier.startswith('IP#'):
        return identifier[3:]
    elif identifier.startswith('USER#'):
        return f"User {identifier[5:]}"
    return identifier


def get_severity_emoji(severity):
    """Get emoji for severity level.

    Args:
        severity: Severity level string

    Returns:
        str: Emoji representing the severity
    """
    severity_emojis = {
        'LOW': '⚠️',
        'MEDIUM': '🟠',
        'HIGH': '🔴',
        'CRITICAL': '🚨'
    }
    return severity_emojis.get(severity, '⚠️')


def format_alert_message(abuse_info, identifier, endpoint, application='PhotoShare'):
    """Format alert message for notifications.

    Args:
        abuse_info: Dict with abuse detection info
        identifier: User identifier
        endpoint: API endpoint
        application: Application name

    Returns:
        dict: {
            'subject': str,
            'text_body': str,
            'html_body': str,
            'sms_body': str
        }
    """
    severity = abuse_info['severity']
    request_count = abuse_info.get('request_count', 0)
    limit = abuse_info.get('limit', 0)
    reason = abuse_info.get('reason', 'Unknown')
    formatted_identifier = format_identifier(identifier)
    emoji = get_severity_emoji(severity)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    # Email subject
    subject = f"{emoji} [{severity}] Rate Limit Alert - {application}"

    # Plain text body
    text_body = f"""
{emoji} RATE LIMIT ALERT - {severity} SEVERITY

Application: {application}
Timestamp: {timestamp}
Identifier: {formatted_identifier}
Endpoint: {endpoint}
Request Count: {request_count}/min
Rate Limit: {limit}/min
Reason: {reason}

{'🛡️  ACTION REQUIRED: This request pattern has been automatically blocked.' if abuse_info.get('should_block') else 'ℹ️  This is a monitoring alert. No automatic action taken.'}

---
This is an automated security alert from {application}.
To adjust alert thresholds or unsubscribe, update your Lambda environment variables.
    """.strip()

    # HTML body
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .alert-header {{
            background: {'#dc3545' if severity in ['HIGH', 'CRITICAL'] else '#fd7e14' if severity == 'MEDIUM' else '#ffc107'};
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            text-align: center;
        }}
        .alert-body {{
            background: #f8f9fa;
            padding: 20px;
            border: 1px solid #dee2e6;
            border-radius: 0 0 8px 8px;
        }}
        .info-row {{
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
            padding: 8px;
            background: white;
            border-radius: 4px;
        }}
        .label {{
            font-weight: bold;
            color: #6c757d;
        }}
        .value {{
            color: #212529;
        }}
        .action-box {{
            margin-top: 20px;
            padding: 15px;
            background: {'#f8d7da' if abuse_info.get('should_block') else '#d1ecf1'};
            border-left: 4px solid {'#dc3545' if abuse_info.get('should_block') else '#17a2b8'};
            border-radius: 4px;
        }}
        .footer {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            font-size: 12px;
            color: #6c757d;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="alert-header">
        <h1>{emoji} RATE LIMIT ALERT</h1>
        <h2>{severity} SEVERITY</h2>
    </div>
    <div class="alert-body">
        <div class="info-row">
            <span class="label">Application:</span>
            <span class="value">{application}</span>
        </div>
        <div class="info-row">
            <span class="label">Timestamp:</span>
            <span class="value">{timestamp}</span>
        </div>
        <div class="info-row">
            <span class="label">Identifier:</span>
            <span class="value">{formatted_identifier}</span>
        </div>
        <div class="info-row">
            <span class="label">Endpoint:</span>
            <span class="value">{endpoint}</span>
        </div>
        <div class="info-row">
            <span class="label">Request Count:</span>
            <span class="value"><strong>{request_count}/min</strong> (Limit: {limit}/min)</span>
        </div>
        <div class="info-row">
            <span class="label">Reason:</span>
            <span class="value">{reason}</span>
        </div>

        <div class="action-box">
            {'🛡️  <strong>ACTION TAKEN:</strong> This request pattern has been automatically blocked.' if abuse_info.get('should_block') else 'ℹ️  <strong>MONITORING ALERT:</strong> No automatic action taken. This is for informational purposes.'}
        </div>
    </div>
    <div class="footer">
        <p>This is an automated security alert from {application}.</p>
        <p>To adjust alert thresholds or modify notification settings, update your Lambda environment variables.</p>
    </div>
</body>
</html>
    """.strip()

    # SMS body (short version)
    sms_body = f"{emoji} ALERT: {application} - {formatted_identifier} - {request_count} req/min on {endpoint} [BLOCKED]" if abuse_info.get('should_block') else f"{emoji} {application}: {formatted_identifier} - {request_count} req/min"

    return {
        'subject': subject,
        'text_body': text_body,
        'html_body': html_body,
        'sms_body': sms_body
    }


def send_email_alert(abuse_info, identifier, endpoint, application='PhotoShare'):
    """Send email alert using AWS SES.

    Args:
        abuse_info: Dict with abuse detection info
        identifier: User identifier
        endpoint: API endpoint
        application: Application name

    Returns:
        dict: {
            'sent': bool,
            'message_id': str or None,
            'error': str or None
        }
    """
    try:
        # Format the alert message
        message = format_alert_message(abuse_info, identifier, endpoint, application)

        # Send email via SES
        response = ses.send_email(
            Source=ADMIN_EMAIL,
            Destination={
                'ToAddresses': [ADMIN_EMAIL]
            },
            Message={
                'Subject': {
                    'Data': message['subject'],
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': message['text_body'],
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': message['html_body'],
                        'Charset': 'UTF-8'
                    }
                }
            }
        )

        message_id = response.get('MessageId')
        print(f"Email sent successfully: {message_id}")

        # Record metric
        try:
            cloudwatch.put_metric_data(
                Namespace='PhotoShare/RateLimiting',
                MetricData=[{
                    'MetricName': 'NotificationsSent',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Application', 'Value': application},
                        {'Name': 'Type', 'Value': 'Email'},
                        {'Name': 'Severity', 'Value': abuse_info['severity']}
                    ]
                }]
            )
        except Exception as metric_error:
            print(f"Error recording metric: {metric_error}")

        return {
            'sent': True,
            'message_id': message_id,
            'error': None
        }

    except Exception as e:
        print(f"Error sending email alert: {e}")
        return {
            'sent': False,
            'message_id': None,
            'error': str(e)
        }


def send_sms_alert(abuse_info, identifier, endpoint, application='PhotoShare'):
    """Send SMS alert using AWS SNS (for critical alerts only).

    Args:
        abuse_info: Dict with abuse detection info
        identifier: User identifier
        endpoint: API endpoint
        application: Application name

    Returns:
        dict: {
            'sent': bool,
            'message_id': str or None,
            'error': str or None
        }
    """
    try:
        # Only send SMS for HIGH or CRITICAL severity
        if abuse_info['severity'] not in ['HIGH', 'CRITICAL']:
            return {
                'sent': False,
                'message_id': None,
                'error': 'SMS only sent for HIGH or CRITICAL alerts'
            }

        # Only send SMS if request count exceeds critical threshold
        request_count = abuse_info.get('request_count', 0)
        if request_count < CRITICAL_THRESHOLD:
            return {
                'sent': False,
                'message_id': None,
                'error': f'SMS only sent when request count >= {CRITICAL_THRESHOLD}'
            }

        # Format the alert message
        message = format_alert_message(abuse_info, identifier, endpoint, application)

        # Send SMS via SNS
        response = sns.publish(
            PhoneNumber=ADMIN_PHONE,
            Message=message['sms_body']
        )

        message_id = response.get('MessageId')
        print(f"SMS sent successfully: {message_id}")

        # Record metric
        try:
            cloudwatch.put_metric_data(
                Namespace='PhotoShare/RateLimiting',
                MetricData=[{
                    'MetricName': 'NotificationsSent',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Application', 'Value': application},
                        {'Name': 'Type', 'Value': 'SMS'},
                        {'Name': 'Severity', 'Value': abuse_info['severity']}
                    ]
                }]
            )
        except Exception as metric_error:
            print(f"Error recording metric: {metric_error}")

        return {
            'sent': True,
            'message_id': message_id,
            'error': None
        }

    except Exception as e:
        print(f"Error sending SMS alert: {e}")
        return {
            'sent': False,
            'message_id': None,
            'error': str(e)
        }


def send_notifications(abuse_info, identifier, endpoint, application='PhotoShare'):
    """Send all appropriate notifications based on severity.

    Args:
        abuse_info: Dict with abuse detection info
        identifier: User identifier
        endpoint: API endpoint
        application: Application name

    Returns:
        dict: {
            'email': dict,
            'sms': dict
        }
    """
    results = {}

    # Always send email for any abuse detection
    results['email'] = send_email_alert(abuse_info, identifier, endpoint, application)

    # Send SMS only for critical alerts (>200 req/min)
    results['sms'] = send_sms_alert(abuse_info, identifier, endpoint, application)

    return results

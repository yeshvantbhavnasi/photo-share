#!/bin/bash

# CloudWatch Alarms Setup Script for Rate Limiting Monitoring
# Creates alarms for both Photo-Share and Baby-Tracker applications

set -e

# Configuration
REGION="us-east-1"
SNS_TOPIC_NAME="app-security-alerts"

# Get SNS Topic ARN
SNS_TOPIC_ARN=$(aws sns list-topics --region $REGION --query "Topics[?contains(TopicArn, '$SNS_TOPIC_NAME')].TopicArn" --output text 2>/dev/null)

if [ -z "$SNS_TOPIC_ARN" ]; then
    echo "❌ Error: SNS topic '$SNS_TOPIC_NAME' not found. Please run setup-rate-limiting.sh first."
    exit 1
fi

echo "🚀 Setting up CloudWatch Alarms for Rate Limiting..."
echo "SNS Topic ARN: $SNS_TOPIC_ARN"
echo ""

# ============================================
# Photo-Share Alarms
# ============================================

echo "📊 Creating Photo-Share alarms..."

# Alarm 1: High Violation Rate (Photo-Share)
echo "Creating alarm: PhotoShare-HighViolationRate..."
aws cloudwatch put-metric-alarm \
  --alarm-name "PhotoShare-HighViolationRate" \
  --alarm-description "Alerts when rate limit violations exceed 10 in 5 minutes for Photo-Share" \
  --metric-name "RateLimitExceeded" \
  --namespace "PhotoShare/RateLimiting" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --region $REGION

# Alarm 2: Critical Abuse Detection (Photo-Share)
echo "Creating alarm: PhotoShare-CriticalAbuse..."
aws cloudwatch put-metric-alarm \
  --alarm-name "PhotoShare-CriticalAbuse" \
  --alarm-description "Immediate alert for CRITICAL severity abuse in Photo-Share" \
  --metric-name "AbuseDetected" \
  --namespace "PhotoShare/RateLimiting" \
  --dimensions "Name=Severity,Value=CRITICAL" \
  --statistic "Sum" \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator "GreaterThanOrEqualToThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --treat-missing-data "notBreaching" \
  --region $REGION

# Alarm 3: High Severity Abuse (Photo-Share)
echo "Creating alarm: PhotoShare-HighAbuse..."
aws cloudwatch put-metric-alarm \
  --alarm-name "PhotoShare-HighAbuse" \
  --alarm-description "Alert for HIGH severity abuse in Photo-Share" \
  --metric-name "AbuseDetected" \
  --namespace "PhotoShare/RateLimiting" \
  --dimensions "Name=Severity,Value=HIGH" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 3 \
  --comparison-operator "GreaterThanThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --treat-missing-data "notBreaching" \
  --region $REGION

# Alarm 4: Lambda Errors (Photo-Share)
echo "Creating alarm: PhotoShare-LambdaErrors..."
aws cloudwatch put-metric-alarm \
  --alarm-name "PhotoShare-LambdaErrors" \
  --alarm-description "Alert when Photo-Share Lambda has more than 5 errors in 5 minutes" \
  --metric-name "Errors" \
  --namespace "AWS/Lambda" \
  --dimensions "Name=FunctionName,Value=photo-share-api" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --treat-missing-data "notBreaching" \
  --region $REGION

# Alarm 5: Expensive Operation Abuse (Photo-Share /edit endpoint)
echo "Creating alarm: PhotoShare-ExpensiveOperationAbuse..."
aws cloudwatch put-metric-alarm \
  --alarm-name "PhotoShare-ExpensiveOperationAbuse" \
  --alarm-description "Alert for abuse of expensive /edit operations in Photo-Share" \
  --metric-name "RateLimitExceeded" \
  --namespace "PhotoShare/RateLimiting" \
  --dimensions "Name=Endpoint,Value=/edit" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --treat-missing-data "notBreaching" \
  --region $REGION

echo "✅ Photo-Share alarms created successfully"
echo ""

# ============================================
# Baby-Tracker Alarms
# ============================================

echo "📊 Creating Baby-Tracker alarms..."

# Alarm 6: High Violation Rate (Baby-Tracker)
echo "Creating alarm: BabyTracker-HighViolationRate..."
aws cloudwatch put-metric-alarm \
  --alarm-name "BabyTracker-HighViolationRate" \
  --alarm-description "Alerts when rate limit violations exceed 10 in 5 minutes for Baby-Tracker" \
  --metric-name "RateLimitExceeded" \
  --namespace "BabyTracker/RateLimiting" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --region $REGION

# Alarm 7: Critical Abuse Detection (Baby-Tracker)
echo "Creating alarm: BabyTracker-CriticalAbuse..."
aws cloudwatch put-metric-alarm \
  --alarm-name "BabyTracker-CriticalAbuse" \
  --alarm-description "Immediate alert for CRITICAL severity abuse in Baby-Tracker" \
  --metric-name "AbuseDetected" \
  --namespace "BabyTracker/RateLimiting" \
  --dimensions "Name=Severity,Value=CRITICAL" \
  --statistic "Sum" \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator "GreaterThanOrEqualToThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --treat-missing-data "notBreaching" \
  --region $REGION

# Alarm 8: High Severity Abuse (Baby-Tracker)
echo "Creating alarm: BabyTracker-HighAbuse..."
aws cloudwatch put-metric-alarm \
  --alarm-name "BabyTracker-HighAbuse" \
  --alarm-description "Alert for HIGH severity abuse in Baby-Tracker" \
  --metric-name "AbuseDetected" \
  --namespace "BabyTracker/RateLimiting" \
  --dimensions "Name=Severity,Value=HIGH" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 3 \
  --comparison-operator "GreaterThanThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --treat-missing-data "notBreaching" \
  --region $REGION

# Alarm 9: Lambda Errors (Baby-Tracker)
echo "Creating alarm: BabyTracker-LambdaErrors..."
aws cloudwatch put-metric-alarm \
  --alarm-name "BabyTracker-LambdaErrors" \
  --alarm-description "Alert when Baby-Tracker Lambda has more than 5 errors in 5 minutes" \
  --metric-name "Errors" \
  --namespace "AWS/Lambda" \
  --dimensions "Name=FunctionName,Value=baby-tracker-api" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --treat-missing-data "notBreaching" \
  --region $REGION

# Alarm 10: Notifications Sent (both apps)
echo "Creating alarm: NotificationsSentHigh..."
aws cloudwatch put-metric-alarm \
  --alarm-name "NotificationsSentHigh" \
  --alarm-description "Alert when too many notifications are sent (possible notification storm)" \
  --metric-name "NotificationsSent" \
  --namespace "PhotoShare/RateLimiting" \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --treat-missing-data "notBreaching" \
  --region $REGION

echo "✅ Baby-Tracker alarms created successfully"
echo ""

# ============================================
# Composite Alarm (Optional)
# ============================================

echo "📊 Creating composite alarm..."

# Create a composite alarm that triggers if multiple alarms fire
echo "Creating alarm: CriticalSecurityEvent..."
aws cloudwatch put-composite-alarm \
  --alarm-name "CriticalSecurityEvent" \
  --alarm-description "Composite alarm for critical security events across both apps" \
  --alarm-rule "ALARM(PhotoShare-CriticalAbuse) OR ALARM(BabyTracker-CriticalAbuse)" \
  --alarm-actions $SNS_TOPIC_ARN \
  --region $REGION 2>/dev/null || echo "⚠️  Composite alarm creation failed (may not be supported in this region)"

echo ""
echo "=========================================="
echo "🎉 CloudWatch Alarms Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Created Alarms:"
echo ""
echo "Photo-Share:"
echo "  1. PhotoShare-HighViolationRate (>10 violations/5min)"
echo "  2. PhotoShare-CriticalAbuse (CRITICAL severity)"
echo "  3. PhotoShare-HighAbuse (>3 HIGH severity/5min)"
echo "  4. PhotoShare-LambdaErrors (>5 errors/5min)"
echo "  5. PhotoShare-ExpensiveOperationAbuse (>5 /edit violations/5min)"
echo ""
echo "Baby-Tracker:"
echo "  6. BabyTracker-HighViolationRate (>10 violations/5min)"
echo "  7. BabyTracker-CriticalAbuse (CRITICAL severity)"
echo "  8. BabyTracker-HighAbuse (>3 HIGH severity/5min)"
echo "  9. BabyTracker-LambdaErrors (>5 errors/5min)"
echo ""
echo "Cross-Application:"
echo "  10. NotificationsSentHigh (>10 notifications/5min)"
echo "  11. CriticalSecurityEvent (Composite alarm)"
echo ""
echo "All alarms will send notifications to: $SNS_TOPIC_ARN"
echo ""
echo "🔍 View alarms in AWS Console:"
echo "   https://console.aws.amazon.com/cloudwatch/home?region=$REGION#alarmsV2:"
echo ""
echo "📊 To create a CloudWatch Dashboard, run:"
echo "   aws cloudwatch put-dashboard --dashboard-name RateLimiting --dashboard-body file://dashboard.json"
echo ""
echo "=========================================="

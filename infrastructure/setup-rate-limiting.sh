#!/bin/bash

# AWS Infrastructure Setup Script for Rate Limiting & Abuse Detection
# This script creates DynamoDB tables, configures SES, and sets up SNS topics

set -e

# Configuration
REGION="us-east-1"
ADMIN_EMAIL="bhavnasiyeshvant@gmail.com"
ADMIN_PHONE="+19808337919"
SNS_TOPIC_NAME="app-security-alerts"

echo "🚀 Setting up Rate Limiting Infrastructure in $REGION..."

# ============================================
# 1. Create DynamoDB Tables
# ============================================

echo ""
echo "📊 Creating DynamoDB Tables..."

# Create RateLimitTracking table
echo "Creating RateLimitTracking table..."
aws dynamodb create-table \
  --table-name RateLimitTracking \
  --attribute-definitions \
    AttributeName=identifier,AttributeType=S \
    AttributeName=requestKey,AttributeType=S \
  --key-schema \
    AttributeName=identifier,KeyType=HASH \
    AttributeName=requestKey,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION \
  --tags Key=Project,Value=PhotoShare Key=Purpose,Value=RateLimiting \
  2>/dev/null || echo "⚠️  RateLimitTracking table already exists"

# Enable TTL on RateLimitTracking table
echo "Enabling TTL on RateLimitTracking table..."
aws dynamodb update-time-to-live \
  --table-name RateLimitTracking \
  --time-to-live-specification "Enabled=true, AttributeName=ttl" \
  --region $REGION \
  2>/dev/null || echo "⚠️  TTL already enabled on RateLimitTracking"

# Create AbuseDetection table
echo "Creating AbuseDetection table..."
aws dynamodb create-table \
  --table-name AbuseDetection \
  --attribute-definitions \
    AttributeName=identifier,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=identifier,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION \
  --tags Key=Project,Value=PhotoShare Key=Purpose,Value=AbuseDetection \
  2>/dev/null || echo "⚠️  AbuseDetection table already exists"

# Enable TTL on AbuseDetection table
echo "Enabling TTL on AbuseDetection table..."
aws dynamodb update-time-to-live \
  --table-name AbuseDetection \
  --time-to-live-specification "Enabled=true, AttributeName=ttl" \
  --region $REGION \
  2>/dev/null || echo "⚠️  TTL already enabled on AbuseDetection"

echo "✅ DynamoDB tables created successfully"

# ============================================
# 2. Configure AWS SES
# ============================================

echo ""
echo "📧 Configuring AWS SES..."

# Verify sender email
echo "Verifying sender email: $ADMIN_EMAIL"
aws ses verify-email-identity \
  --email-address $ADMIN_EMAIL \
  --region $REGION \
  2>/dev/null || echo "⚠️  Email already verified or verification pending"

echo ""
echo "⚠️  IMPORTANT: Check your email ($ADMIN_EMAIL) and click the verification link from AWS SES"
echo "   The email should arrive within a few minutes."
echo ""

# Check SES sending limits
echo "Checking SES account status..."
aws ses get-send-quota --region $REGION

echo ""
echo "💡 If you're in SES Sandbox mode:"
echo "   1. You can only send to verified email addresses"
echo "   2. Daily sending limit is 200 emails"
echo "   3. Request production access: https://console.aws.amazon.com/ses/home?region=$REGION#/account"
echo ""

# ============================================
# 3. Create SNS Topic and Subscriptions
# ============================================

echo ""
echo "📢 Creating SNS Topic..."

# Create SNS topic
SNS_TOPIC_ARN=$(aws sns create-topic \
  --name $SNS_TOPIC_NAME \
  --region $REGION \
  --tags Key=Project,Value=PhotoShare Key=Purpose,Value=SecurityAlerts \
  --output text \
  --query 'TopicArn' 2>/dev/null || \
  aws sns list-topics --region $REGION --query "Topics[?contains(TopicArn, '$SNS_TOPIC_NAME')].TopicArn" --output text)

echo "✅ SNS Topic ARN: $SNS_TOPIC_ARN"

# Subscribe email to SNS topic
echo "Subscribing email to SNS topic: $ADMIN_EMAIL"
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol email \
  --notification-endpoint $ADMIN_EMAIL \
  --region $REGION \
  2>/dev/null || echo "⚠️  Email subscription already exists"

# Subscribe SMS to SNS topic
echo "Subscribing SMS to SNS topic: $ADMIN_PHONE"
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol sms \
  --notification-endpoint $ADMIN_PHONE \
  --region $REGION \
  2>/dev/null || echo "⚠️  SMS subscription already exists"

echo ""
echo "⚠️  IMPORTANT: Check your email ($ADMIN_EMAIL) and confirm the SNS subscription"
echo "   The confirmation email should arrive within a few minutes."
echo ""

# ============================================
# 4. Create IAM Policy for Lambda
# ============================================

echo ""
echo "🔐 Creating IAM Policy for Lambda Functions..."

POLICY_NAME="PhotoShareRateLimitingPolicy"

# Create IAM policy JSON
cat > /tmp/rate-limiting-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:$REGION:*:table/RateLimitTracking",
        "arn:aws:dynamodb:$REGION:*:table/AbuseDetection"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "$SNS_TOPIC_ARN"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create or update the policy
POLICY_ARN=$(aws iam create-policy \
  --policy-name $POLICY_NAME \
  --policy-document file:///tmp/rate-limiting-policy.json \
  --description "Policy for Photo Share rate limiting and abuse detection" \
  --output text \
  --query 'Policy.Arn' 2>/dev/null || \
  aws iam list-policies --query "Policies[?PolicyName=='$POLICY_NAME'].Arn" --output text)

echo "✅ IAM Policy ARN: $POLICY_ARN"

# Clean up temp file
rm /tmp/rate-limiting-policy.json

# ============================================
# 5. Display Configuration Summary
# ============================================

echo ""
echo "=========================================="
echo "🎉 Infrastructure Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Configuration Summary:"
echo ""
echo "DynamoDB Tables:"
echo "  • RateLimitTracking (with TTL enabled)"
echo "  • AbuseDetection (with TTL enabled)"
echo ""
echo "AWS SES:"
echo "  • Sender Email: $ADMIN_EMAIL (verification pending)"
echo ""
echo "SNS Topic:"
echo "  • Topic ARN: $SNS_TOPIC_ARN"
echo "  • Email Subscription: $ADMIN_EMAIL (confirmation pending)"
echo "  • SMS Subscription: $ADMIN_PHONE"
echo ""
echo "IAM Policy:"
echo "  • Policy ARN: $POLICY_ARN"
echo ""
echo "=========================================="
echo "⚠️  Next Steps:"
echo "=========================================="
echo ""
echo "1. ✉️  Check your email and VERIFY the SES sender address"
echo "2. ✉️  Check your email and CONFIRM the SNS subscription"
echo "3. 🔐 Attach the IAM policy to your Lambda execution role(s):"
echo "   aws iam attach-role-policy \\"
echo "     --role-name <YOUR_LAMBDA_ROLE_NAME> \\"
echo "     --policy-arn $POLICY_ARN"
echo ""
echo "4. 🚀 Deploy the Lambda functions with the following environment variables:"
echo "   RATE_LIMIT_TABLE=RateLimitTracking"
echo "   ABUSE_TABLE=AbuseDetection"
echo "   SNS_TOPIC_ARN=$SNS_TOPIC_ARN"
echo "   ADMIN_EMAIL=$ADMIN_EMAIL"
echo "   ADMIN_PHONE=$ADMIN_PHONE"
echo "   RATE_LIMIT_THRESHOLD=100"
echo "   CRITICAL_THRESHOLD=200"
echo ""
echo "=========================================="

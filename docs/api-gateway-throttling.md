# API Gateway Throttling Configuration

This document provides instructions for configuring API Gateway throttling as an additional layer of protection for both Photo-Share and Baby-Tracker applications.

## Overview

API Gateway throttling provides a **backstop** layer of protection that:
- Prevents Lambda from being overwhelmed by excessive requests
- Provides immediate request rejection at the edge (before reaching Lambda)
- Complements the application-level rate limiting in Lambda
- Protects against DDoS attacks and accidental request storms

## Architecture

```
Request → API Gateway (throttle) → Lambda (rate limit) → DynamoDB
          ↓                         ↓
      429 Response            Rate Limit Tracker
                                    ↓
                              Email/SMS Alerts
```

## Photo-Share Throttling Configuration

### Global Settings

Set account-level throttling limits (applies to all APIs):

```bash
aws apigateway update-account \
  --patch-operations \
    op='replace',path='/throttle/burstLimit',value='200' \
    op='replace',path='/throttle/rateLimit',value='100'
```

### Per-Stage Throttling

Configure throttling for the `prod` stage:

```bash
# Get API ID
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='photo-share-api'].ApiId" --output text)

# Update stage throttling
aws apigatewayv2 update-stage \
  --api-id $API_ID \
  --stage-name prod \
  --route-settings '{
    "$default": {
      "ThrottlingBurstLimit": 200,
      "ThrottlingRateLimit": 100
    },
    "POST /share": {
      "ThrottlingBurstLimit": 20,
      "ThrottlingRateLimit": 10
    },
    "POST /edit": {
      "ThrottlingBurstLimit": 10,
      "ThrottlingRateLimit": 5
    },
    "POST /upload": {
      "ThrottlingBurstLimit": 40,
      "ThrottlingRateLimit": 20
    }
  }'
```

### Recommended Limits (Photo-Share)

| Route | Rate Limit (req/sec) | Burst Limit | Rationale |
|-------|---------------------|-------------|-----------|
| Global (default) | 100 | 200 | General API traffic |
| `POST /share` | 10 | 20 | Share link creation |
| `POST /edit` | 5 | 10 | AI image editing (expensive) |
| `POST /upload` | 20 | 40 | Photo uploads |
| `GET /albums` | 50 | 100 | Album listing |
| `GET /timeline` | 50 | 100 | Timeline queries |

## Baby-Tracker Throttling Configuration

### Per-Stage Throttling

Configure throttling for the `prod` stage:

```bash
# Get API ID
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='baby-tracker-api'].ApiId" --output text)

# Update stage throttling
aws apigatewayv2 update-stage \
  --api-id $API_ID \
  --stage-name prod \
  --route-settings '{
    "$default": {
      "ThrottlingBurstLimit": 200,
      "ThrottlingRateLimit": 100
    },
    "POST /activities": {
      "ThrottlingBurstLimit": 60,
      "ThrottlingRateLimit": 30
    },
    "POST /milestones": {
      "ThrottlingBurstLimit": 40,
      "ThrottlingRateLimit": 20
    },
    "POST /upload": {
      "ThrottlingBurstLimit": 30,
      "ThrottlingRateLimit": 15
    }
  }'
```

### Recommended Limits (Baby-Tracker)

| Route | Rate Limit (req/sec) | Burst Limit | Rationale |
|-------|---------------------|-------------|-----------|
| Global (default) | 100 | 200 | General API traffic |
| `POST /activities` | 30 | 60 | Activity logging |
| `POST /milestones` | 20 | 40 | Milestone creation |
| `POST /upload` | 15 | 30 | Photo/video uploads |
| `GET /twins` | 50 | 100 | Twin profile queries |

## Understanding Rate Limit vs Burst Limit

- **Rate Limit**: Average requests per second allowed over time
- **Burst Limit**: Maximum requests allowed in a short burst

Example:
- Rate Limit: 10 req/sec
- Burst Limit: 20

This allows:
- Steady traffic: 10 requests per second sustained
- Bursty traffic: Up to 20 requests in a single second, then throttled back to 10/sec

## Automated Configuration Script

Create a script to configure both APIs:

```bash
#!/bin/bash

# Configuration
REGION="us-east-1"

# Photo-Share Configuration
echo "Configuring Photo-Share API Gateway throttling..."
PHOTO_API_ID=$(aws apigatewayv2 get-apis --region $REGION --query "Items[?Name=='photo-share-api'].ApiId" --output text)

if [ -n "$PHOTO_API_ID" ]; then
    aws apigatewayv2 update-stage \
      --api-id $PHOTO_API_ID \
      --stage-name prod \
      --throttle-settings RateLimit=100,BurstLimit=200 \
      --region $REGION

    echo "✅ Photo-Share throttling configured"
else
    echo "⚠️  Photo-Share API not found"
fi

# Baby-Tracker Configuration
echo "Configuring Baby-Tracker API Gateway throttling..."
BABY_API_ID=$(aws apigatewayv2 get-apis --region $REGION --query "Items[?Name=='baby-tracker-api'].ApiId" --output text)

if [ -n "$BABY_API_ID" ]; then
    aws apigatewayv2 update-stage \
      --api-id $BABY_API_ID \
      --stage-name prod \
      --throttle-settings RateLimit=100,BurstLimit=200 \
      --region $REGION

    echo "✅ Baby-Tracker throttling configured"
else
    echo "⚠️  Baby-Tracker API not found"
fi

echo "🎉 API Gateway throttling configuration complete!"
```

## Monitoring Throttling

### CloudWatch Metrics

API Gateway automatically publishes these metrics:

1. **Count**: Total API requests
2. **4XXError**: Client errors (including 429 from throttling)
3. **5XXError**: Server errors
4. **Latency**: Request processing time

### View Throttling in CloudWatch

```bash
# Get throttling metrics for Photo-Share
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiId,Value=$PHOTO_API_ID \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

### Create Throttling Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "PhotoShare-APIGatewayThrottling" \
  --alarm-description "Alert when API Gateway is throttling requests" \
  --metric-name "Count" \
  --namespace "AWS/ApiGateway" \
  --dimensions Name=ApiId,Value=$PHOTO_API_ID \
  --statistic "Sum" \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5000 \
  --comparison-operator "GreaterThanThreshold" \
  --alarm-actions $SNS_TOPIC_ARN \
  --region us-east-1
```

## Testing Throttling

### Load Test with Apache Bench

Test the throttling limits:

```bash
# Test Photo-Share global limit (100 req/sec)
ab -n 500 -c 50 -H "Authorization: Bearer $JWT_TOKEN" \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/albums

# Test Photo-Share /edit endpoint (5 req/sec)
ab -n 100 -c 10 -p edit_request.json -T application/json -H "Authorization: Bearer $JWT_TOKEN" \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/edit

# Test Baby-Tracker activities (30 req/sec)
ab -n 300 -c 30 -p activity.json -T application/json -H "Authorization: Bearer $JWT_TOKEN" \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/activities
```

Expected results:
- Requests within limit: HTTP 200
- Throttled requests: HTTP 429 (Too Many Requests)

### Verify Response Headers

Throttled responses include these headers:

```
HTTP/1.1 429 Too Many Requests
X-Amzn-ErrorType: TooManyRequestsException
X-Amzn-RequestId: abc-123-def
Retry-After: 5
```

## Per-User Throttling with API Keys (Optional)

For API key-based authentication, configure per-key throttling:

```bash
# Create usage plan
aws apigateway create-usage-plan \
  --name "PhotoSharePremium" \
  --throttle burstLimit=500,rateLimit=250 \
  --quota limit=10000,period=DAY \
  --api-stages apiId=$API_ID,stage=prod

# Associate API key with usage plan
aws apigateway create-usage-plan-key \
  --usage-plan-id $USAGE_PLAN_ID \
  --key-id $API_KEY_ID \
  --key-type API_KEY
```

## Best Practices

1. **Layer Defense**:
   - API Gateway throttling: Fast rejection at the edge
   - Lambda rate limiting: Intelligent abuse detection with notifications
   - CloudFront: DDoS protection and caching (if used)

2. **Set Appropriate Limits**:
   - Start conservative, monitor, then adjust
   - Expensive operations (AI, uploads) should have lower limits
   - Read operations can have higher limits than writes

3. **Monitor and Alert**:
   - Set CloudWatch alarms for throttling events
   - Review metrics weekly to adjust limits
   - Coordinate with application-level rate limit thresholds

4. **Documentation**:
   - Document all throttling rules
   - Include rationale for each limit
   - Keep limits in sync with Lambda rate limiting

5. **Testing**:
   - Load test before production deployment
   - Test both normal and burst traffic patterns
   - Verify 429 responses are handled gracefully

## Troubleshooting

### High 429 Error Rate

If you see excessive 429 errors:

1. Check if limits are too aggressive:
   ```bash
   aws apigatewayv2 get-stage --api-id $API_ID --stage-name prod
   ```

2. Increase limits temporarily:
   ```bash
   aws apigatewayv2 update-stage \
     --api-id $API_ID \
     --stage-name prod \
     --throttle-settings RateLimit=200,BurstLimit=400
   ```

3. Investigate request patterns in CloudWatch

### Legitimate Users Being Throttled

If real users are affected:

1. **Option 1**: Increase global limits
2. **Option 2**: Implement per-user API keys with higher limits
3. **Option 3**: Use Cognito authorizer with custom throttling logic
4. **Option 4**: Add caching to reduce duplicate requests

## Cost Implications

API Gateway throttling is **free** - you're not charged for throttled requests.

Pricing (as of 2024):
- First 333 million requests/month: $1.00 per million
- Next 667 million requests/month: $0.90 per million
- Over 1 billion requests/month: $0.80 per million

Throttled requests **do not count** toward your bill.

## Summary

✅ **Implemented**:
- Global throttling at API Gateway level
- Per-route throttling for expensive operations
- CloudWatch monitoring and alarms
- Load testing procedures

✅ **Benefits**:
- Protects Lambda from overload
- Reduces costs (throttled requests are free)
- Fast rejection at the edge (low latency)
- Complements application-level rate limiting

✅ **Next Steps**:
1. Run load tests to validate limits
2. Monitor for 2-4 weeks
3. Adjust limits based on actual traffic patterns
4. Set up CloudWatch Dashboard for visualization

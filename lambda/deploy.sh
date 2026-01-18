#!/bin/bash
set -e

# Configuration
FUNCTION_NAME="photo-share-api"
REGION="us-east-1"
PHOTOS_TABLE="PhotosMetadata"
SHARE_LINKS_TABLE="ShareLinks"
CLOUDFRONT_DOMAIN="d1nf5k4wr11svj.cloudfront.net"

echo "Deploying Photo Share API Lambda..."

# Create IAM role for Lambda if it doesn't exist
ROLE_NAME="photo-share-lambda-role"
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    echo "Creating IAM role..."

    # Create trust policy
    cat > /tmp/trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create role
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --region $REGION

    # Attach basic execution policy
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    # Create DynamoDB policy
    cat > /tmp/dynamodb-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:$REGION:*:table/$PHOTOS_TABLE",
        "arn:aws:dynamodb:$REGION:*:table/$PHOTOS_TABLE/index/*",
        "arn:aws:dynamodb:$REGION:*:table/$SHARE_LINKS_TABLE"
      ]
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name DynamoDBAccess \
        --policy-document file:///tmp/dynamodb-policy.json

    # Wait for role to propagate
    echo "Waiting for IAM role to propagate..."
    sleep 10

    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
fi

echo "Using role: $ROLE_ARN"

# Package Lambda function
echo "Packaging Lambda function..."
cd "$(dirname "$0")"
zip -j /tmp/lambda-function.zip index.py

# Check if function exists
FUNCTION_EXISTS=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || echo "")

if [ -z "$FUNCTION_EXISTS" ]; then
    echo "Creating Lambda function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler index.lambda_handler \
        --zip-file fileb:///tmp/lambda-function.zip \
        --timeout 30 \
        --memory-size 256 \
        --environment "Variables={PHOTOS_TABLE=$PHOTOS_TABLE,SHARE_LINKS_TABLE=$SHARE_LINKS_TABLE,CLOUDFRONT_DOMAIN=$CLOUDFRONT_DOMAIN}" \
        --region $REGION
else
    echo "Updating Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb:///tmp/lambda-function.zip \
        --region $REGION

    # Wait for update to complete
    sleep 5

    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment "Variables={PHOTOS_TABLE=$PHOTOS_TABLE,SHARE_LINKS_TABLE=$SHARE_LINKS_TABLE,CLOUDFRONT_DOMAIN=$CLOUDFRONT_DOMAIN}" \
        --region $REGION
fi

# Get Lambda ARN
LAMBDA_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)
echo "Lambda ARN: $LAMBDA_ARN"

# Create or get API Gateway
API_NAME="photo-share-api"
API_ID=$(aws apigatewayv2 get-apis --region $REGION --query "Items[?Name=='$API_NAME'].ApiId" --output text 2>/dev/null || echo "")

if [ -z "$API_ID" ]; then
    echo "Creating API Gateway..."

    API_ID=$(aws apigatewayv2 create-api \
        --name $API_NAME \
        --protocol-type HTTP \
        --cors-configuration "AllowOrigins=*,AllowMethods=GET,OPTIONS,AllowHeaders=Content-Type" \
        --region $REGION \
        --query 'ApiId' \
        --output text)

    # Create Lambda integration
    INTEGRATION_ID=$(aws apigatewayv2 create-integration \
        --api-id $API_ID \
        --integration-type AWS_PROXY \
        --integration-uri $LAMBDA_ARN \
        --payload-format-version 2.0 \
        --region $REGION \
        --query 'IntegrationId' \
        --output text)

    # Create default route
    aws apigatewayv2 create-route \
        --api-id $API_ID \
        --route-key 'GET /{proxy+}' \
        --target "integrations/$INTEGRATION_ID" \
        --region $REGION

    aws apigatewayv2 create-route \
        --api-id $API_ID \
        --route-key 'OPTIONS /{proxy+}' \
        --target "integrations/$INTEGRATION_ID" \
        --region $REGION

    # Create stage
    aws apigatewayv2 create-stage \
        --api-id $API_ID \
        --stage-name prod \
        --auto-deploy \
        --region $REGION

    # Add Lambda permission for API Gateway
    aws lambda add-permission \
        --function-name $FUNCTION_NAME \
        --statement-id apigateway-access \
        --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        --source-arn "arn:aws:execute-api:$REGION:*:$API_ID/*" \
        --region $REGION 2>/dev/null || true
fi

# Get API endpoint
API_ENDPOINT=$(aws apigatewayv2 get-api --api-id $API_ID --region $REGION --query 'ApiEndpoint' --output text)

echo ""
echo "=========================================="
echo "Lambda deployed successfully!"
echo "=========================================="
echo "API Gateway ID: $API_ID"
echo "API Endpoint: $API_ENDPOINT/prod"
echo ""
echo "Test endpoints:"
echo "  $API_ENDPOINT/prod/albums"
echo "  $API_ENDPOINT/prod/album?id=<album-id>"
echo "  $API_ENDPOINT/prod/share?token=<token>"
echo ""
echo "Add this to your .env file:"
echo "API_ENDPOINT=$API_ENDPOINT/prod"

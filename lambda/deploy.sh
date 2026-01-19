#!/bin/bash
set -e

# Configuration
FUNCTION_NAME="photo-share-api"
REGION="us-east-1"
PHOTOS_TABLE="PhotosMetadata"
SHARE_LINKS_TABLE="ShareLinks"
CLOUDFRONT_DOMAIN="d1nf5k4wr11svj.cloudfront.net"
PHOTOS_BUCKET="yeshvant-photos-storage-2026"

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
        "dynamodb:Scan",
        "dynamodb:PutItem",
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

    # Create S3 policy for image editing
    cat > /tmp/s3-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::yeshvant-photos-storage-2026/*"
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name S3Access \
        --policy-document file:///tmp/s3-policy.json

    # Create Bedrock policy for AI features (includes inference-profile for new Stability AI models)
    cat > /tmp/bedrock-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/stability.*",
        "arn:aws:bedrock:*:*:inference-profile/us.stability.*"
      ]
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name BedrockAccess \
        --policy-document file:///tmp/bedrock-policy.json

    # Wait for role to propagate
    echo "Waiting for IAM role to propagate..."
    sleep 10

    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
fi

echo "Using role: $ROLE_ARN"

# Package Lambda function with dependencies
echo "Packaging Lambda function..."
cd "$(dirname "$0")"

# Create a temporary directory for packaging
PACKAGE_DIR="/tmp/lambda-package"
rm -rf $PACKAGE_DIR
mkdir -p $PACKAGE_DIR

# Install Pillow for Lambda (Amazon Linux 2)
echo "Installing Pillow for Lambda..."
python3 -m pip install --platform manylinux2014_x86_64 --target $PACKAGE_DIR --implementation cp --python-version 3.11 --only-binary=:all: Pillow -q

# Copy Lambda code
cp index.py $PACKAGE_DIR/
cp image_processor.py $PACKAGE_DIR/

# Create deployment package
cd $PACKAGE_DIR
zip -r /tmp/lambda-function.zip . -q
cd -

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
        --timeout 120 \
        --memory-size 1024 \
        --environment "Variables={PHOTOS_TABLE=$PHOTOS_TABLE,SHARE_LINKS_TABLE=$SHARE_LINKS_TABLE,CLOUDFRONT_DOMAIN=$CLOUDFRONT_DOMAIN,PHOTOS_BUCKET=$PHOTOS_BUCKET}" \
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
        --timeout 120 \
        --memory-size 1024 \
        --environment "Variables={PHOTOS_TABLE=$PHOTOS_TABLE,SHARE_LINKS_TABLE=$SHARE_LINKS_TABLE,CLOUDFRONT_DOMAIN=$CLOUDFRONT_DOMAIN,PHOTOS_BUCKET=$PHOTOS_BUCKET}" \
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
        --cors-configuration "AllowOrigins=*,AllowMethods=GET,POST,DELETE,OPTIONS,AllowHeaders=Content-Type" \
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

    # Create routes for all HTTP methods
    aws apigatewayv2 create-route \
        --api-id $API_ID \
        --route-key 'GET /{proxy+}' \
        --target "integrations/$INTEGRATION_ID" \
        --region $REGION

    aws apigatewayv2 create-route \
        --api-id $API_ID \
        --route-key 'POST /{proxy+}' \
        --target "integrations/$INTEGRATION_ID" \
        --region $REGION

    aws apigatewayv2 create-route \
        --api-id $API_ID \
        --route-key 'DELETE /{proxy+}' \
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

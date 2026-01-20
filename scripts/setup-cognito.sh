#!/bin/bash

# Setup Cognito User Pool for Photo Share Application
# Run this script to create the Cognito resources

set -e

REGION="us-east-1"
POOL_NAME="photo-share-users"
CLIENT_NAME="photo-share-web"
API_ID="yd3tspcwml"  # Your API Gateway ID

echo "Creating Cognito User Pool..."

# Create user pool
POOL_RESULT=$(aws cognito-idp create-user-pool \
  --pool-name "$POOL_NAME" \
  --auto-verified-attributes email \
  --username-attributes email \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 8,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": false
    }
  }' \
  --schema '[
    {
      "Name": "email",
      "Required": true,
      "Mutable": true
    }
  ]' \
  --account-recovery-setting '{
    "RecoveryMechanisms": [
      {"Priority": 1, "Name": "verified_email"}
    ]
  }' \
  --region "$REGION" \
  --output json)

USER_POOL_ID=$(echo "$POOL_RESULT" | jq -r '.UserPool.Id')
echo "Created User Pool: $USER_POOL_ID"

# Create app client (no secret for browser-based auth)
echo "Creating App Client..."

CLIENT_RESULT=$(aws cognito-idp create-user-pool-client \
  --user-pool-id "$USER_POOL_ID" \
  --client-name "$CLIENT_NAME" \
  --no-generate-secret \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH \
  --supported-identity-providers COGNITO \
  --prevent-user-existence-errors ENABLED \
  --region "$REGION" \
  --output json)

CLIENT_ID=$(echo "$CLIENT_RESULT" | jq -r '.UserPoolClient.ClientId')
echo "Created App Client: $CLIENT_ID"

# Create API Gateway Authorizer
echo "Creating API Gateway Cognito Authorizer..."

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POOL_ARN="arn:aws:cognito-idp:${REGION}:${ACCOUNT_ID}:userpool/${USER_POOL_ID}"

AUTHORIZER_RESULT=$(aws apigateway create-authorizer \
  --rest-api-id "$API_ID" \
  --name "CognitoAuthorizer" \
  --type COGNITO_USER_POOLS \
  --provider-arns "$POOL_ARN" \
  --identity-source "method.request.header.Authorization" \
  --region "$REGION" \
  --output json)

AUTHORIZER_ID=$(echo "$AUTHORIZER_RESULT" | jq -r '.id')
echo "Created Authorizer: $AUTHORIZER_ID"

# Output configuration
echo ""
echo "=========================================="
echo "Cognito Setup Complete!"
echo "=========================================="
echo ""
echo "Add these to your .env.local file:"
echo ""
echo "NEXT_PUBLIC_COGNITO_USER_POOL_ID=$USER_POOL_ID"
echo "NEXT_PUBLIC_COGNITO_CLIENT_ID=$CLIENT_ID"
echo "NEXT_PUBLIC_COGNITO_REGION=$REGION"
echo ""
echo "Authorizer ID (for API Gateway config): $AUTHORIZER_ID"
echo ""
echo "Next steps:"
echo "1. Add the environment variables to your .env.local file"
echo "2. Configure API Gateway methods to use the authorizer (except /share GET)"
echo "3. Deploy the API Gateway"
echo ""

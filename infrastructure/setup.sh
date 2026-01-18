#!/bin/bash
set -e

# Family Photo Sharing Platform - AWS Infrastructure Setup
# This script creates all necessary AWS resources

# Configuration
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PHOTOS_BUCKET="yeshvant-photos-storage-2026"
WEBSITE_BUCKET="yeshvant-photos-website-2026"
PHOTOS_TABLE="PhotosMetadata"
SHARE_LINKS_TABLE="ShareLinks"
TIMESTAMP=$(date +%s)

echo "=========================================="
echo "Family Photo Sharing Platform Setup"
echo "=========================================="
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo "Photos Bucket: $PHOTOS_BUCKET"
echo "Website Bucket: $WEBSITE_BUCKET"
echo "=========================================="

# Set region
aws configure set region $REGION
echo "✓ Region set to $REGION"

# -----------------------------------------
# Step 1: Create S3 Bucket for Photos
# -----------------------------------------
echo ""
echo "Step 1: Creating S3 bucket for photos..."

aws s3api create-bucket \
    --bucket $PHOTOS_BUCKET \
    --region $REGION 2>/dev/null || echo "Bucket $PHOTOS_BUCKET may already exist"

# Block public access
aws s3api put-public-access-block \
    --bucket $PHOTOS_BUCKET \
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable CORS for presigned URL uploads
aws s3api put-bucket-cors \
    --bucket $PHOTOS_BUCKET \
    --cors-configuration '{
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
                "AllowedOrigins": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3000
            }
        ]
    }'

echo "✓ Photos bucket created and configured"

# -----------------------------------------
# Step 2: Create S3 Bucket for Website
# -----------------------------------------
echo ""
echo "Step 2: Creating S3 bucket for website..."

aws s3api create-bucket \
    --bucket $WEBSITE_BUCKET \
    --region $REGION 2>/dev/null || echo "Bucket $WEBSITE_BUCKET may already exist"

# Block public access (will be served via CloudFront)
aws s3api put-public-access-block \
    --bucket $WEBSITE_BUCKET \
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "✓ Website bucket created"

# -----------------------------------------
# Step 3: Create DynamoDB Tables
# -----------------------------------------
echo ""
echo "Step 3: Creating DynamoDB tables..."

# PhotosMetadata table
aws dynamodb create-table \
    --table-name $PHOTOS_TABLE \
    --attribute-definitions \
        AttributeName=pk,AttributeType=S \
        AttributeName=sk,AttributeType=S \
        AttributeName=albumId,AttributeType=S \
        AttributeName=uploadDate,AttributeType=S \
    --key-schema \
        AttributeName=pk,KeyType=HASH \
        AttributeName=sk,KeyType=RANGE \
    --global-secondary-indexes \
        "[{
            \"IndexName\": \"albumId-uploadDate-index\",
            \"KeySchema\": [{\"AttributeName\":\"albumId\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"uploadDate\",\"KeyType\":\"RANGE\"}],
            \"Projection\": {\"ProjectionType\":\"ALL\"},
            \"ProvisionedThroughput\": {\"ReadCapacityUnits\":5,\"WriteCapacityUnits\":5}
        }]" \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region $REGION 2>/dev/null || echo "Table $PHOTOS_TABLE may already exist"

# ShareLinks table
aws dynamodb create-table \
    --table-name $SHARE_LINKS_TABLE \
    --attribute-definitions \
        AttributeName=linkId,AttributeType=S \
    --key-schema \
        AttributeName=linkId,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region $REGION 2>/dev/null || echo "Table $SHARE_LINKS_TABLE may already exist"

echo "✓ DynamoDB tables created"
echo "  Waiting for tables to become active..."
aws dynamodb wait table-exists --table-name $PHOTOS_TABLE
aws dynamodb wait table-exists --table-name $SHARE_LINKS_TABLE
echo "✓ Tables are active"

# -----------------------------------------
# Step 4: Create CloudFront Origin Access Control
# -----------------------------------------
echo ""
echo "Step 4: Creating CloudFront Origin Access Control..."

OAC_ID=$(aws cloudfront create-origin-access-control \
    --origin-access-control-config "{
        \"Name\": \"photo-share-oac-$TIMESTAMP\",
        \"Description\": \"OAC for photo sharing platform\",
        \"SigningProtocol\": \"sigv4\",
        \"SigningBehavior\": \"always\",
        \"OriginAccessControlOriginType\": \"s3\"
    }" \
    --query 'OriginAccessControl.Id' \
    --output text 2>/dev/null) || OAC_ID=""

if [ -z "$OAC_ID" ]; then
    echo "  Looking for existing OAC..."
    OAC_ID=$(aws cloudfront list-origin-access-controls \
        --query "OriginAccessControlList.Items[?contains(Name, 'photo-share-oac')].Id | [0]" \
        --output text)
fi

echo "✓ Origin Access Control ID: $OAC_ID"

# -----------------------------------------
# Step 5: Create CloudFront Distribution
# -----------------------------------------
echo ""
echo "Step 5: Creating CloudFront distribution..."

# Create distribution config
DISTRIBUTION_CONFIG=$(cat <<EOF
{
    "CallerReference": "photo-share-$TIMESTAMP",
    "Comment": "Family Photo Sharing Platform",
    "Enabled": true,
    "DefaultRootObject": "index.html",
    "Origins": {
        "Quantity": 2,
        "Items": [
            {
                "Id": "website-origin",
                "DomainName": "$WEBSITE_BUCKET.s3.$REGION.amazonaws.com",
                "S3OriginConfig": {
                    "OriginAccessIdentity": ""
                },
                "OriginAccessControlId": "$OAC_ID"
            },
            {
                "Id": "photos-origin",
                "DomainName": "$PHOTOS_BUCKET.s3.$REGION.amazonaws.com",
                "S3OriginConfig": {
                    "OriginAccessIdentity": ""
                },
                "OriginAccessControlId": "$OAC_ID"
            }
        ]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "website-origin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
            "Quantity": 2,
            "Items": ["GET", "HEAD"],
            "CachedMethods": {
                "Quantity": 2,
                "Items": ["GET", "HEAD"]
            }
        },
        "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
        "Compress": true
    },
    "CacheBehaviors": {
        "Quantity": 2,
        "Items": [
            {
                "PathPattern": "/photos/*",
                "TargetOriginId": "photos-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 2,
                    "Items": ["GET", "HEAD"],
                    "CachedMethods": {
                        "Quantity": 2,
                        "Items": ["GET", "HEAD"]
                    }
                },
                "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
                "Compress": true
            },
            {
                "PathPattern": "/thumbnails/*",
                "TargetOriginId": "photos-origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 2,
                    "Items": ["GET", "HEAD"],
                    "CachedMethods": {
                        "Quantity": 2,
                        "Items": ["GET", "HEAD"]
                    }
                },
                "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
                "Compress": true
            }
        ]
    },
    "CustomErrorResponses": {
        "Quantity": 1,
        "Items": [
            {
                "ErrorCode": 404,
                "ResponsePagePath": "/index.html",
                "ResponseCode": "200",
                "ErrorCachingMinTTL": 300
            }
        ]
    },
    "PriceClass": "PriceClass_100"
}
EOF
)

DISTRIBUTION_RESULT=$(aws cloudfront create-distribution \
    --distribution-config "$DISTRIBUTION_CONFIG" \
    --output json 2>/dev/null) || DISTRIBUTION_RESULT=""

if [ -n "$DISTRIBUTION_RESULT" ]; then
    DISTRIBUTION_ID=$(echo $DISTRIBUTION_RESULT | jq -r '.Distribution.Id')
    CLOUDFRONT_DOMAIN=$(echo $DISTRIBUTION_RESULT | jq -r '.Distribution.DomainName')
    echo "✓ CloudFront Distribution created"
    echo "  Distribution ID: $DISTRIBUTION_ID"
    echo "  Domain: https://$CLOUDFRONT_DOMAIN"
else
    echo "  Looking for existing distribution..."
    DISTRIBUTION_ID=$(aws cloudfront list-distributions \
        --query "DistributionList.Items[?Comment=='Family Photo Sharing Platform'].Id | [0]" \
        --output text)
    CLOUDFRONT_DOMAIN=$(aws cloudfront list-distributions \
        --query "DistributionList.Items[?Comment=='Family Photo Sharing Platform'].DomainName | [0]" \
        --output text)
    echo "✓ Using existing distribution: $DISTRIBUTION_ID"
    echo "  Domain: https://$CLOUDFRONT_DOMAIN"
fi

# -----------------------------------------
# Step 6: Update S3 Bucket Policies for CloudFront
# -----------------------------------------
echo ""
echo "Step 6: Updating S3 bucket policies for CloudFront access..."

# Website bucket policy
aws s3api put-bucket-policy \
    --bucket $WEBSITE_BUCKET \
    --policy "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
            {
                \"Sid\": \"AllowCloudFrontServicePrincipal\",
                \"Effect\": \"Allow\",
                \"Principal\": {
                    \"Service\": \"cloudfront.amazonaws.com\"
                },
                \"Action\": \"s3:GetObject\",
                \"Resource\": \"arn:aws:s3:::$WEBSITE_BUCKET/*\",
                \"Condition\": {
                    \"StringEquals\": {
                        \"AWS:SourceArn\": \"arn:aws:cloudfront::$ACCOUNT_ID:distribution/$DISTRIBUTION_ID\"
                    }
                }
            }
        ]
    }"

# Photos bucket policy
aws s3api put-bucket-policy \
    --bucket $PHOTOS_BUCKET \
    --policy "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
            {
                \"Sid\": \"AllowCloudFrontServicePrincipal\",
                \"Effect\": \"Allow\",
                \"Principal\": {
                    \"Service\": \"cloudfront.amazonaws.com\"
                },
                \"Action\": \"s3:GetObject\",
                \"Resource\": \"arn:aws:s3:::$PHOTOS_BUCKET/*\",
                \"Condition\": {
                    \"StringEquals\": {
                        \"AWS:SourceArn\": \"arn:aws:cloudfront::$ACCOUNT_ID:distribution/$DISTRIBUTION_ID\"
                    }
                }
            }
        ]
    }"

echo "✓ Bucket policies updated"

# -----------------------------------------
# Save Configuration
# -----------------------------------------
echo ""
echo "Saving configuration..."

cat > /Users/yeshvant/photo-share/.env <<EOF
# AWS Configuration for Photo Sharing Platform
AWS_REGION=$REGION
PHOTOS_BUCKET=$PHOTOS_BUCKET
WEBSITE_BUCKET=$WEBSITE_BUCKET
PHOTOS_TABLE=$PHOTOS_TABLE
SHARE_LINKS_TABLE=$SHARE_LINKS_TABLE
CLOUDFRONT_DISTRIBUTION_ID=$DISTRIBUTION_ID
CLOUDFRONT_DOMAIN=$CLOUDFRONT_DOMAIN
NEXT_PUBLIC_CLOUDFRONT_URL=https://$CLOUDFRONT_DOMAIN
EOF

echo "✓ Configuration saved to /Users/yeshvant/photo-share/.env"

# -----------------------------------------
# Summary
# -----------------------------------------
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Resources Created:"
echo "  • S3 Bucket (Photos): $PHOTOS_BUCKET"
echo "  • S3 Bucket (Website): $WEBSITE_BUCKET"
echo "  • DynamoDB Table: $PHOTOS_TABLE"
echo "  • DynamoDB Table: $SHARE_LINKS_TABLE"
echo "  • CloudFront Distribution: $DISTRIBUTION_ID"
echo ""
echo "Your website will be available at:"
echo "  https://$CLOUDFRONT_DOMAIN"
echo ""
echo "Next Steps:"
echo "  1. cd /Users/yeshvant/photo-share/website"
echo "  2. npm install"
echo "  3. npm run build"
echo "  4. ../scripts/deploy.sh"
echo ""

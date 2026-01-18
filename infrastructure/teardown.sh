#!/bin/bash
set -e

# Family Photo Sharing Platform - Teardown Script
# This script removes all AWS resources

# Load configuration
if [ -f /Users/yeshvant/photo-share/.env ]; then
    source /Users/yeshvant/photo-share/.env
else
    echo "Error: .env file not found. Please run setup.sh first."
    exit 1
fi

echo "=========================================="
echo "Family Photo Sharing Platform Teardown"
echo "=========================================="
echo ""
echo "WARNING: This will delete ALL resources including:"
echo "  • S3 Bucket: $PHOTOS_BUCKET (with all photos)"
echo "  • S3 Bucket: $WEBSITE_BUCKET"
echo "  • DynamoDB Table: $PHOTOS_TABLE"
echo "  • DynamoDB Table: $SHARE_LINKS_TABLE"
echo "  • CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Teardown cancelled."
    exit 0
fi

echo ""
echo "Starting teardown..."

# -----------------------------------------
# Step 1: Disable and Delete CloudFront Distribution
# -----------------------------------------
echo ""
echo "Step 1: Disabling CloudFront distribution..."

# Get the current ETag
ETAG=$(aws cloudfront get-distribution-config \
    --id $CLOUDFRONT_DISTRIBUTION_ID \
    --query 'ETag' \
    --output text)

# Get current config and disable it
aws cloudfront get-distribution-config \
    --id $CLOUDFRONT_DISTRIBUTION_ID \
    --query 'DistributionConfig' \
    --output json > /tmp/cf-config.json

# Update Enabled to false
jq '.Enabled = false' /tmp/cf-config.json > /tmp/cf-config-disabled.json

# Update the distribution
aws cloudfront update-distribution \
    --id $CLOUDFRONT_DISTRIBUTION_ID \
    --if-match $ETAG \
    --distribution-config file:///tmp/cf-config-disabled.json > /dev/null

echo "✓ Distribution disabled"
echo "  Waiting for distribution to be deployed (this may take several minutes)..."

aws cloudfront wait distribution-deployed --id $CLOUDFRONT_DISTRIBUTION_ID

# Get new ETag after update
ETAG=$(aws cloudfront get-distribution-config \
    --id $CLOUDFRONT_DISTRIBUTION_ID \
    --query 'ETag' \
    --output text)

# Delete the distribution
aws cloudfront delete-distribution \
    --id $CLOUDFRONT_DISTRIBUTION_ID \
    --if-match $ETAG

echo "✓ CloudFront distribution deleted"

# -----------------------------------------
# Step 2: Empty and Delete S3 Buckets
# -----------------------------------------
echo ""
echo "Step 2: Deleting S3 buckets..."

# Empty and delete photos bucket
aws s3 rm s3://$PHOTOS_BUCKET --recursive 2>/dev/null || true
aws s3api delete-bucket --bucket $PHOTOS_BUCKET 2>/dev/null || true
echo "✓ Photos bucket deleted"

# Empty and delete website bucket
aws s3 rm s3://$WEBSITE_BUCKET --recursive 2>/dev/null || true
aws s3api delete-bucket --bucket $WEBSITE_BUCKET 2>/dev/null || true
echo "✓ Website bucket deleted"

# -----------------------------------------
# Step 3: Delete DynamoDB Tables
# -----------------------------------------
echo ""
echo "Step 3: Deleting DynamoDB tables..."

aws dynamodb delete-table --table-name $PHOTOS_TABLE 2>/dev/null || true
aws dynamodb delete-table --table-name $SHARE_LINKS_TABLE 2>/dev/null || true
echo "✓ DynamoDB tables deleted"

# -----------------------------------------
# Step 4: Clean up OAC
# -----------------------------------------
echo ""
echo "Step 4: Cleaning up Origin Access Controls..."

OAC_LIST=$(aws cloudfront list-origin-access-controls \
    --query "OriginAccessControlList.Items[?contains(Name, 'photo-share-oac')].[Id,ETag]" \
    --output text)

while read -r OAC_ID OAC_ETAG; do
    if [ -n "$OAC_ID" ] && [ "$OAC_ID" != "None" ]; then
        aws cloudfront delete-origin-access-control \
            --id $OAC_ID \
            --if-match $OAC_ETAG 2>/dev/null || true
        echo "  Deleted OAC: $OAC_ID"
    fi
done <<< "$OAC_LIST"

echo "✓ Origin Access Controls cleaned up"

# -----------------------------------------
# Clean up local config
# -----------------------------------------
echo ""
echo "Removing local configuration..."
rm -f /Users/yeshvant/photo-share/.env
echo "✓ Local configuration removed"

echo ""
echo "=========================================="
echo "Teardown Complete!"
echo "=========================================="
echo ""
echo "All AWS resources have been deleted."
echo ""

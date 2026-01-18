#!/bin/bash
set -e

# Family Photo Sharing Platform - Deployment Script
# This script builds and deploys the Next.js website to S3

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WEBSITE_DIR="$PROJECT_DIR/website"

# Load configuration
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
else
    echo "Warning: .env file not found. Using default values."
    WEBSITE_BUCKET="yeshvant-photos-website-2026"
    CLOUDFRONT_DISTRIBUTION_ID=""
fi

echo "=========================================="
echo "Family Photo Sharing - Deploy Website"
echo "=========================================="
echo ""

# Check if website directory exists
if [ ! -d "$WEBSITE_DIR" ]; then
    echo "Error: Website directory not found at $WEBSITE_DIR"
    exit 1
fi

cd "$WEBSITE_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Build the website
echo ""
echo "Building website..."
npm run build

# Check if build succeeded
if [ ! -d "out" ]; then
    echo "Error: Build failed - 'out' directory not found"
    exit 1
fi

# Deploy to S3
echo ""
echo "Deploying to S3..."
aws s3 sync out/ s3://$WEBSITE_BUCKET/ \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "*.html"

# Upload HTML files with different cache settings
aws s3 sync out/ s3://$WEBSITE_BUCKET/ \
    --cache-control "public, max-age=0, must-revalidate" \
    --include "*.html"

echo "✓ Files uploaded to S3"

# Invalidate CloudFront cache
if [ -n "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
    echo ""
    echo "Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
        --paths "/*" > /dev/null
    echo "✓ CloudFront cache invalidated"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""

if [ -n "$CLOUDFRONT_DOMAIN" ]; then
    echo "Your website is available at:"
    echo "  https://$CLOUDFRONT_DOMAIN"
else
    echo "Your website is deployed to:"
    echo "  s3://$WEBSITE_BUCKET"
fi

echo ""

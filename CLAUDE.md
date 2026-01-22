# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A serverless photo sharing platform built on AWS. Users upload photos from Mac, organize into albums, and share with family via unique links. Features include timeline view, duplicate detection, AI-powered image editing, and Cognito authentication.

## Development Commands

### Website (Next.js)
```bash
cd website
npm install
npm run dev                    # Start dev server at http://localhost:3000
npm run build                  # Production build
npm run lint                   # Run ESLint
npm run test:e2e               # Run Playwright E2E tests
npm run test:e2e:ui            # Run E2E tests with UI
npm run test:e2e:headed        # Run E2E tests in headed mode
npm run test:e2e:debug         # Debug E2E tests
```

### Lambda (Python)
```bash
cd lambda
python -m pytest                            # Run all tests
python -m pytest tests/test_index.py        # Run specific test file
python -m pytest tests/test_index.py::test_get_albums  # Run single test
python -m pytest -v                         # Verbose output
```

### Deployment
```bash
./infrastructure/setup.sh      # Create all AWS resources
./scripts/deploy.sh            # Deploy website to S3/CloudFront
./infrastructure/teardown.sh   # Delete all AWS resources (WARNING: deletes all data)
```

### Photo Upload
```bash
# Install dependencies
pip install boto3 pillow python-dotenv

# Upload folder as album
python scripts/upload.py ~/Photos/Vacation2024 --album-name "Vacation 2024"

# Upload with share link (expires in 30 days)
python scripts/upload.py ~/Photos/Wedding --share --expires 30
```

## Architecture

### Three-Tier Serverless Design
1. **Frontend**: Next.js 14 (App Router) with React, TypeScript, Tailwind CSS
   - Static site hosted in S3, served via CloudFront
   - Client-side routing with protected routes (Cognito auth)
   - Components: Gallery, Lightbox, UploadDropzone, EditModal, ShareButton

2. **API Layer**: AWS Lambda (Python 3.11) + API Gateway
   - Single Lambda function (`lambda/index.py`) handles all API routes
   - Rate limiting with CloudWatch metrics and SNS notifications
   - Image processing: rotate, enhance, upscale, remove background, style transfer
   - Duplicate detection using perceptual hashing

3. **Storage**:
   - **S3**: Photos (`photos/{userId}/{albumId}/{photoId}.ext`), thumbnails, website static files
   - **DynamoDB**: Two tables with specific access patterns (see below)
   - **CloudFront**: CDN for global delivery with OAC (Origin Access Control)

### DynamoDB Schema (Single Table Design)

**PhotosMetadata Table**:
- `pk=USER#{userId}, sk=ALBUM#{albumId}` - Album metadata
- `pk=ALBUM#{albumId}, sk=PHOTO#{photoId}` - Photo in album
- `pk=USER#{userId}, sk=DATE#{YYYY-MM-DD}#PHOTO#{photoId}` - Timeline index (no GSI needed)

**ShareLinks Table**:
- `pk=linkId` - Share link with albumId, expiresAt, accessCount

### Key Design Patterns

**Timeline View**: Uses composite sort key `DATE#{YYYY-MM-DD}#PHOTO#{photoId}` on main table instead of GSI. Query with `pk=USER#{userId}` and `sk` begins_with/between for date ranges. Sorted descending (newest first) with ScanIndexForward=False.

**Soft Delete**: Photos marked with `hidden=true` and `hiddenAt` timestamp instead of deletion. Filtered out in `is_photo_visible()` function.

**Authentication**: Cognito JWT tokens extracted via `get_user_id_from_event()` which tries multiple methods (HTTP API JWT authorizer, REST API authorizer, manual JWT decode). Protected routes checked in Lambda handler.

**Rate Limiting**: Per-user/IP limits enforced in Lambda (`rate_limiter.py`). Abuse detection sends notifications via SNS (`notification_handler.py`). Can be disabled with `RATE_LIMITING_ENABLED=false`.

**Upload Flow**:
1. Client requests presigned URLs (POST `/upload`)
2. Client uploads photo + thumbnail directly to S3
3. Client confirms upload (POST `/upload/complete`)
4. Lambda saves metadata to DynamoDB

### Frontend Route Structure

```
app/
├── (auth)/               # Auth pages (login, signup, verify)
├── (main)/               # Protected main app
│   ├── page.tsx          # Home (redirects to /albums)
│   ├── albums/page.tsx   # Album list
│   ├── album/page.tsx    # Album detail with photos
│   ├── timeline/page.tsx # Timeline view by date
│   ├── upload/page.tsx   # Upload interface
│   └── duplicates/page.tsx # Duplicate detection
└── shared/               # Public share link pages (no auth)
```

### Important Files

**Lambda**:
- `lambda/index.py` - Main handler with all API routes
- `lambda/image_processor.py` - Image editing operations
- `lambda/duplicate_detector.py` - Perceptual hash-based duplicate detection
- `lambda/rate_limiter.py` - Rate limiting and abuse detection
- `lambda/notification_handler.py` - SNS notifications

**Frontend**:
- `website/lib/api-client.ts` - Client-side API wrapper
- `website/lib/types.ts` - TypeScript interfaces
- `website/components/Gallery.tsx` - Photo grid with lazy loading
- `website/components/Lightbox.tsx` - Full-screen photo viewer
- `website/components/UploadDropzone.tsx` - Drag-drop upload with client-side thumbnails

**Scripts**:
- `scripts/upload.py` - Batch upload from Mac with thumbnail generation
- `scripts/backfill_timeline.py` - Migrate existing photos to timeline index
- `scripts/migrate-to-user.py` - Migrate from default-user to Cognito user

## Testing

**Lambda Tests** (pytest):
- Located in `lambda/tests/`
- `conftest.py` sets up fixtures: mock_dynamodb, mock_s3, sample JWT tokens
- Must set `AWS_DEFAULT_REGION=us-east-1` before boto3 imports
- Tests cover: albums, photos, timeline, share links, authentication

**E2E Tests** (Playwright):
- Located in `website/e2e/`
- Config: `playwright.config.ts` (baseURL: CloudFront distribution)
- Run against live deployment (not local dev server)

## Environment Variables

Required in `.env` file:
```
AWS_REGION=us-east-1
PHOTOS_BUCKET=yeshvant-photos-storage-2026
PHOTOS_TABLE=PhotosMetadata
SHARE_LINKS_TABLE=ShareLinks
CLOUDFRONT_DOMAIN=d1nf5k4wr11svj.cloudfront.net
USER_ID=default-user  # For upload script
RATE_LIMITING_ENABLED=true
```

Frontend also uses `.env.local` for Cognito configuration.

## Common Workflows

### Adding a New API Endpoint
1. Add route handler in `lambda/index.py` (around line 729+)
2. Handle CORS with `cors_response(status, body)`
3. Extract user_id via `get_user_id_from_event(event)` if protected
4. Use `DecimalEncoder` for JSON responses (DynamoDB returns Decimal)
5. Add to protected_routes list if authentication required
6. Create frontend client method in `website/lib/api-client.ts`

### Modifying DynamoDB Schema
- Uses single-table design - avoid creating GSIs
- Composite sort keys for efficient queries (e.g., DATE#YYYY-MM-DD#PHOTO#id)
- Always include userId in partition key for user isolation
- Use `is_photo_visible()` to filter hidden/metadata files

### Image Processing
- Operations handled by `image_processor.py`
- Uses PIL (Pillow) for basic operations (rotate, enhance)
- Placeholders for upscale, remove_bg, style_transfer (integrate external APIs as needed)
- Results stored in S3 with new photoId, linked to original via `originalPhotoId`

### CI/CD
- GitHub Actions workflows in `.github/workflows/`
- `deploy.yml` - Builds and deploys on push to master
- `security-scan.yml` - Security scanning with Trivy

## Important Notes

- Filenames starting with `.` (macOS metadata) are filtered out in `is_photo_visible()`
- Share links at `/shared` route are NOT protected (public access)
- Edit operations at `/edit` route are also public (allows shared album viewers to use AI features)
- CloudFront caching: 24h for photos, 1h for thumbnails, no-cache for API
- S3 buckets are private - all access via CloudFront with OAC
- DynamoDB uses consistent read=False for better performance (eventual consistency acceptable)

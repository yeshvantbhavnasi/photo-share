# Family Photo Sharing Platform

Share photos with family by uploading Mac folders as albums with unique share links.

## Features

- **Folder to Album Upload** - Each Mac folder becomes an album in S3
- **Per-Album Share Links** - Generate unique URLs for specific albums
- **Simple Photo Grid** - Fast-loading grid view of photos with lazy loading
- **Click to Enlarge** - Full-size photo viewing in a lightbox
- **No Auth for Viewers** - Family just clicks link and views

## Quick Start

### 1. Set Up AWS Infrastructure

```bash
cd photo-share
./infrastructure/setup.sh
```

This creates:
- S3 bucket for photos (`yeshvant-photos-storage-2026`)
- S3 bucket for website (`yeshvant-photos-website-2026`)
- DynamoDB tables (`PhotosMetadata`, `ShareLinks`)
- CloudFront distribution for fast global delivery

### 2. Build and Deploy Website

```bash
cd website
npm install
npm run build
../scripts/deploy.sh
```

### 3. Upload Photos

```bash
# Install Python dependencies
pip install boto3 pillow python-dotenv

# Upload a folder
python scripts/upload.py ~/Photos/Vacation2024 --album-name "Vacation 2024"

# Upload and create share link
python scripts/upload.py ~/Photos/Wedding --share --expires 30
```

## Project Structure

```
photo-share/
├── infrastructure/
│   ├── setup.sh              # AWS resource creation
│   ├── teardown.sh           # AWS resource cleanup
│   └── cloudfront-policy.json
├── website/
│   ├── app/                  # Next.js App Router pages
│   │   ├── layout.tsx        # Root layout
│   │   ├── page.tsx          # Home page
│   │   ├── albums/           # Albums listing and detail
│   │   ├── upload/           # Upload interface
│   │   └── share/[token]/    # Shared album view
│   ├── components/
│   │   ├── Gallery.tsx       # Photo grid
│   │   ├── Lightbox.tsx      # Full-screen viewer
│   │   ├── UploadDropzone.tsx
│   │   ├── ShareButton.tsx
│   │   └── AlbumCard.tsx
│   ├── lib/
│   │   ├── s3.ts             # S3 utilities
│   │   ├── dynamodb.ts       # DynamoDB operations
│   │   ├── api-client.ts     # Client-side API
│   │   └── types.ts          # TypeScript types
│   └── package.json
├── scripts/
│   ├── upload.py             # Batch upload from Mac
│   └── deploy.sh             # Deploy website to S3
├── .env                      # Environment variables (created by setup.sh)
└── README.md
```

## AWS Resources

### S3 Buckets

**Photos Storage** (`yeshvant-photos-storage-2026`):
```
/photos/{user_id}/{album_id}/{photo_id}.{ext}
/thumbnails/{user_id}/{album_id}/{photo_id}_thumb.{ext}
```

**Website** (`yeshvant-photos-website-2026`):
- Static Next.js build output
- Served via CloudFront

### DynamoDB Tables

**PhotosMetadata**:
- PK: `USER#{userId}` or `ALBUM#{albumId}`
- SK: `ALBUM#{albumId}` or `PHOTO#{photoId}`
- GSI: `albumId-uploadDate-index`

**ShareLinks**:
- PK: `linkId` (unique share token)
- Attributes: albumId, createdAt, expiresAt, accessCount

### CloudFront Distribution

- HTTPS only
- Origin Access Control (OAC) for secure S3 access
- Cache behaviors optimized for static assets

## User Flow

```
You (Mac)                        Family (Browser)
─────────────────────────────    ─────────────────────────────
~/Photos/Vacation2024/    ──▶    Share link: .../share/abc123
   ├── beach.jpg                    ┌─────────────────────┐
   ├── sunset.jpg          ──▶     │ ▢ ▢ ▢ ▢ ▢ ▢ ▢ ▢ │
   └── group.jpg                    │ Simple Photo Grid   │
                                    └─────────────────────┘
```

## Cost Estimates (Monthly)

| Storage | 10GB | 100GB | 2TB |
|---------|------|-------|-----|
| S3 Standard | $0.23 | $2.30 | $46 |
| S3 Infrequent Access | $0.13 | $1.25 | $25 |

Additional:
- CloudFront transfer: ~$0.085/GB
- DynamoDB: Free tier covers most use cases
- Total for typical use (10GB photos, moderate viewing): **< $5/month**

## Commands Reference

```bash
# Setup AWS infrastructure
./infrastructure/setup.sh

# Teardown all resources
./infrastructure/teardown.sh

# Deploy website
./scripts/deploy.sh

# Upload folder as album
python scripts/upload.py /path/to/folder

# Upload with custom name
python scripts/upload.py /path/to/folder --album-name "Custom Name"

# Upload and generate share link
python scripts/upload.py /path/to/folder --share

# Upload with expiring share link (30 days)
python scripts/upload.py /path/to/folder --share --expires 30
```

## Security

- S3 buckets are private (not directly accessible)
- All access via CloudFront with HTTPS
- Share links use cryptographically random tokens
- Optional link expiration
- No user accounts needed (admin-only upload)

## Development

```bash
cd website
npm install
npm run dev
```

Open http://localhost:3000

## Cleanup

To remove all AWS resources:

```bash
./infrastructure/teardown.sh
```

**Warning**: This permanently deletes all photos and data!

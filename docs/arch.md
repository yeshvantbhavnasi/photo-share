# Bhavnasi Share - Architecture Documentation

## Overview

Bhavnasi Share is a serverless family photo sharing platform built on AWS. It allows uploading photos from Mac folders and sharing them via unique links with family and friends.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BHAVNASI SHARE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   Web Browser    │
                    │  (Next.js App)   │
                    └────────┬─────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLOUDFRONT CDN                                     │
│                     d1nf5k4wr11svj.cloudfront.net                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Behaviors:                                                          │   │
│  │  • /*           → S3 Website Bucket (static Next.js app)            │   │
│  │  • /photos/*    → S3 Storage Bucket (original photos)               │   │
│  │  • /thumbnails/* → S3 Storage Bucket (thumbnails)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   S3: Website    │ │  S3: Storage     │ │   API Gateway    │
│                  │ │                  │ │                  │
│ Static HTML/JS   │ │ /photos/...      │ │  /prod/albums    │
│ Next.js export   │ │ /thumbnails/...  │ │  /prod/timeline  │
│                  │ │                  │ │  /prod/share     │
└──────────────────┘ └──────────────────┘ └────────┬─────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │     Lambda       │
                                          │  photo-share-api │
                                          │                  │
                                          │  Python 3.11     │
                                          │  boto3           │
                                          └────────┬─────────┘
                                                   │
                                    ┌──────────────┴──────────────┐
                                    ▼                             ▼
                           ┌──────────────────┐          ┌──────────────────┐
                           │    DynamoDB      │          │    DynamoDB      │
                           │ PhotosMetadata   │          │   ShareLinks     │
                           │                  │          │                  │
                           │ Albums & Photos  │          │ Share tokens     │
                           └──────────────────┘          └──────────────────┘
```

## AWS Resources

### S3 Buckets

| Bucket | Purpose |
|--------|---------|
| `yeshvant-photos-website-2026` | Static Next.js website |
| `yeshvant-photos-storage-2026` | Photo & thumbnail storage |

### DynamoDB Tables

#### PhotosMetadata (Single Table Design with Duplicate Items)

**Primary Key:** `pk` (Partition Key) + `sk` (Sort Key)

**Design Pattern:** Each photo is stored TWICE with different keys to support multiple access patterns without GSI.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SINGLE TABLE DESIGN (DUPLICATE ITEMS)                     │
├──────────────────────┬────────────────────────────────────┬─────────────────┤
│ pk                   │ sk                                 │ Purpose         │
├──────────────────────┼────────────────────────────────────┼─────────────────┤
│ USER#default-user    │ ALBUM#abc123                       │ Album metadata  │
│ USER#default-user    │ ALBUM#def456                       │ Album metadata  │
│ USER#default-user    │ DATE#2026-01-18#PHOTO#111          │ Timeline query  │
│ USER#default-user    │ DATE#2026-01-18#PHOTO#222          │ Timeline query  │
│ USER#default-user    │ DATE#2026-01-15#PHOTO#333          │ Timeline query  │
│ ALBUM#abc123         │ PHOTO#111                          │ Album photos    │
│ ALBUM#abc123         │ PHOTO#222                          │ Album photos    │
│ ALBUM#def456         │ PHOTO#333                          │ Album photos    │
└──────────────────────┴────────────────────────────────────┴─────────────────┘
```

**Why duplicate items instead of GSI?**
- Strongly consistent reads (GSI is eventually consistent)
- No additional GSI cost
- Simpler pricing model
- Better for small-medium scale

#### ShareLinks

| Attribute | Type | Description |
|-----------|------|-------------|
| `linkId` (PK) | String | Unique share token |
| `albumId` | String | Album being shared |
| `createdAt` | String | ISO timestamp |
| `expiresAt` | String | Optional expiration |
| `accessCount` | Number | View counter |

### Lambda Function

**Name:** `photo-share-api`
**Runtime:** Python 3.11
**Memory:** 128 MB
**Timeout:** 30 seconds

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/albums` | List all albums |
| GET | `/album?id=X` | Get album photos |
| GET | `/timeline` | Get all photos by date |
| GET | `/photos?startDate=X&endDate=Y` | Filter photos by date range |
| GET | `/share?token=X` | Validate share link & get album |

### CloudFront Distribution

**Domain:** `d1nf5k4wr11svj.cloudfront.net`

**Cache Behaviors:**
- Default (`/*`): Website bucket, 1 day cache
- `/photos/*`: Storage bucket, 1 year cache (immutable)
- `/thumbnails/*`: Storage bucket, 1 year cache

**CloudFront Function:** `index-rewrite`
- Appends `index.html` to directory URLs

## Data Flow

### Photo Upload (CLI)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Mac Folder │────▶│   upload.py │────▶│     S3      │────▶│  DynamoDB   │
│  ~/Photos   │     │  (Python)   │     │   Bucket    │     │  Metadata   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Pillow     │
                    │ (Thumbnails)│
                    └─────────────┘
```

### Photo Viewing (Web)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│ CloudFront  │────▶│   Lambda    │────▶│  DynamoDB   │
│             │     │             │     │   (API)     │     │  (Query)    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       │                   ▼
       │            ┌─────────────┐
       └───────────▶│     S3      │
         (images)   │  (Photos)   │
                    └─────────────┘
```

## Query Patterns

### Access Pattern → DynamoDB Query

| What you want | How to query |
|--------------|--------------|
| All albums for user | `pk = USER#userId`, `sk begins_with ALBUM#` |
| All photos in album | `pk = ALBUM#albumId`, `sk begins_with PHOTO#` |
| All photos by date | `pk = USER#userId`, `sk begins_with DATE#` |
| Photos in date range | `pk = USER#userId`, `sk between DATE#2026-01-01 and DATE#2026-01-31~` |
| Validate share link | ShareLinks table: `linkId = token` |

### Query Examples (Python/boto3)

```python
# Get all albums
table.query(
    KeyConditionExpression=Key('pk').eq('USER#default-user') &
                          Key('sk').begins_with('ALBUM#')
)

# Get photos in album
table.query(
    KeyConditionExpression=Key('pk').eq('ALBUM#abc123') &
                          Key('sk').begins_with('PHOTO#')
)

# Get timeline (all photos by date, newest first)
table.query(
    KeyConditionExpression=Key('pk').eq('USER#default-user') &
                          Key('sk').begins_with('DATE#'),
    ScanIndexForward=False  # Descending order
)

# Get photos in date range
table.query(
    KeyConditionExpression=Key('pk').eq('USER#default-user') &
                          Key('sk').between('DATE#2026-01-15', 'DATE#2026-01-20~')
)
```

## Security

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SECURITY MODEL                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  S3 Buckets          → Private (Block Public Access)                        │
│                      → Only accessible via CloudFront OAC                   │
│                                                                             │
│  CloudFront          → HTTPS only                                           │
│                      → Origin Access Control (OAC) for S3                   │
│                                                                             │
│  Share Links         → Cryptographically random tokens                      │
│                      → Optional expiration                                  │
│                      → No authentication required for viewers               │
│                                                                             │
│  Admin (You)         → AWS credentials for upload script                    │
│                      → No web-based admin interface                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Cost Breakdown (Estimated Monthly)

| Service | Usage | Cost |
|---------|-------|------|
| S3 Standard | 10 GB photos | ~$0.23 |
| S3 Requests | ~10,000 GET | ~$0.004 |
| CloudFront | 50 GB transfer | ~$4.25 |
| DynamoDB On-Demand | ~100k reads/writes | ~$0.25 |
| Lambda | ~10k invocations | Free tier |
| **Total** | | **~$5-10/month** |

For 2TB storage, expect ~$50-60/month (mostly S3 storage).

## File Structure

```
photo-share/
├── lambda/
│   └── index.py              # Lambda function code
├── scripts/
│   └── upload.py             # CLI upload tool
├── website/
│   ├── app/
│   │   ├── page.tsx          # Home page
│   │   ├── albums/           # Album views
│   │   ├── timeline/         # Timeline view (date-based)
│   │   ├── shared/           # Shared album view
│   │   └── upload/           # Upload page
│   ├── components/
│   │   ├── Gallery.tsx       # Photo grid
│   │   └── Lightbox.tsx      # Full-screen viewer
│   └── lib/
│       ├── api-client.ts     # API client
│       └── types.ts          # TypeScript types
├── infrastructure/
│   └── setup.sh              # AWS setup script
└── docs/
    └── arch.md               # This file
```

## URLs

| Resource | URL |
|----------|-----|
| Website | https://d1nf5k4wr11svj.cloudfront.net |
| API | https://yd3tspcwml.execute-api.us-east-1.amazonaws.com/prod |
| GitHub | https://github.com/yeshvantbhavnasi/photo-share |

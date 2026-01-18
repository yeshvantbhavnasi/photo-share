import { S3Client, PutObjectCommand, ListObjectsV2Command } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const REGION = process.env.AWS_REGION || 'us-east-1';
const PHOTOS_BUCKET = process.env.NEXT_PUBLIC_PHOTOS_BUCKET || 'yeshvant-photos-storage-2026';

// S3 client - only used server-side or in upload script
let s3Client: S3Client | null = null;

function getS3Client(): S3Client {
  if (!s3Client) {
    s3Client = new S3Client({ region: REGION });
  }
  return s3Client;
}

export interface PresignedUrlResult {
  uploadUrl: string;
  photoKey: string;
  thumbnailKey: string;
}

export async function generatePresignedUploadUrl(
  userId: string,
  albumId: string,
  photoId: string,
  contentType: string
): Promise<PresignedUrlResult> {
  const client = getS3Client();
  const ext = contentType.split('/')[1] || 'jpg';
  const photoKey = `photos/${userId}/${albumId}/${photoId}.${ext}`;
  const thumbnailKey = `thumbnails/${userId}/${albumId}/${photoId}_thumb.${ext}`;

  const command = new PutObjectCommand({
    Bucket: PHOTOS_BUCKET,
    Key: photoKey,
    ContentType: contentType,
  });

  const uploadUrl = await getSignedUrl(client, command, { expiresIn: 3600 });

  return {
    uploadUrl,
    photoKey,
    thumbnailKey,
  };
}

export async function listAlbumPhotos(userId: string, albumId: string): Promise<string[]> {
  const client = getS3Client();
  const prefix = `photos/${userId}/${albumId}/`;

  const command = new ListObjectsV2Command({
    Bucket: PHOTOS_BUCKET,
    Prefix: prefix,
  });

  const response = await client.send(command);

  return (response.Contents || [])
    .map(obj => obj.Key!)
    .filter(key => key !== prefix);
}

export function getPhotoUrl(key: string): string {
  const cloudfrontUrl = process.env.NEXT_PUBLIC_CLOUDFRONT_URL;
  if (cloudfrontUrl) {
    return `${cloudfrontUrl}/${key}`;
  }
  return `https://${PHOTOS_BUCKET}.s3.${REGION}.amazonaws.com/${key}`;
}

export function getThumbnailUrl(photoKey: string): string {
  const thumbnailKey = photoKey
    .replace('photos/', 'thumbnails/')
    .replace(/\.(\w+)$/, '_thumb.$1');
  return getPhotoUrl(thumbnailKey);
}

export function getPhotoIdFromKey(key: string): string {
  const filename = key.split('/').pop() || '';
  return filename.replace(/\.\w+$/, '');
}

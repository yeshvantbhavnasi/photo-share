import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import {
  DynamoDBDocumentClient,
  PutCommand,
  GetCommand,
  QueryCommand,
  UpdateCommand,
  DeleteCommand
} from '@aws-sdk/lib-dynamodb';
import { nanoid } from 'nanoid';

const REGION = process.env.AWS_REGION || 'us-east-1';
const PHOTOS_TABLE = process.env.PHOTOS_TABLE || 'PhotosMetadata';
const SHARE_LINKS_TABLE = process.env.SHARE_LINKS_TABLE || 'ShareLinks';

let docClient: DynamoDBDocumentClient | null = null;

function getDocClient(): DynamoDBDocumentClient {
  if (!docClient) {
    const client = new DynamoDBClient({ region: REGION });
    docClient = DynamoDBDocumentClient.from(client, {
      marshallOptions: {
        removeUndefinedValues: true,
      },
    });
  }
  return docClient;
}

// Photo types
export interface Photo {
  photoId: string;
  albumId: string;
  userId: string;
  filename: string;
  s3Key: string;
  thumbnailKey: string;
  contentType: string;
  size: number;
  uploadDate: string;
}

export interface Album {
  albumId: string;
  userId: string;
  name: string;
  description?: string;
  coverPhotoKey?: string;
  photoCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface ShareLink {
  linkId: string;
  albumId: string;
  userId: string;
  createdAt: string;
  expiresAt?: string;
  accessCount: number;
  createdBy: string;
}

// Album operations
export async function createAlbum(
  userId: string,
  name: string,
  description?: string
): Promise<Album> {
  const client = getDocClient();
  const albumId = nanoid(12);
  const now = new Date().toISOString();

  const album: Album = {
    albumId,
    userId,
    name,
    description,
    photoCount: 0,
    createdAt: now,
    updatedAt: now,
  };

  await client.send(new PutCommand({
    TableName: PHOTOS_TABLE,
    Item: {
      pk: `USER#${userId}`,
      sk: `ALBUM#${albumId}`,
      ...album,
    },
  }));

  return album;
}

export async function getAlbum(userId: string, albumId: string): Promise<Album | null> {
  const client = getDocClient();

  const response = await client.send(new GetCommand({
    TableName: PHOTOS_TABLE,
    Key: {
      pk: `USER#${userId}`,
      sk: `ALBUM#${albumId}`,
    },
  }));

  if (!response.Item) return null;

  const { pk, sk, ...album } = response.Item;
  return album as Album;
}

export async function listUserAlbums(userId: string): Promise<Album[]> {
  const client = getDocClient();

  const response = await client.send(new QueryCommand({
    TableName: PHOTOS_TABLE,
    KeyConditionExpression: 'pk = :pk AND begins_with(sk, :sk)',
    ExpressionAttributeValues: {
      ':pk': `USER#${userId}`,
      ':sk': 'ALBUM#',
    },
  }));

  return (response.Items || []).map(item => {
    const { pk, sk, ...album } = item;
    return album as Album;
  });
}

export async function updateAlbumPhotoCount(
  userId: string,
  albumId: string,
  increment: number
): Promise<void> {
  const client = getDocClient();

  await client.send(new UpdateCommand({
    TableName: PHOTOS_TABLE,
    Key: {
      pk: `USER#${userId}`,
      sk: `ALBUM#${albumId}`,
    },
    UpdateExpression: 'SET photoCount = photoCount + :inc, updatedAt = :now',
    ExpressionAttributeValues: {
      ':inc': increment,
      ':now': new Date().toISOString(),
    },
  }));
}

// Photo operations
export async function savePhotoMetadata(photo: Photo): Promise<void> {
  const client = getDocClient();

  await client.send(new PutCommand({
    TableName: PHOTOS_TABLE,
    Item: {
      pk: `ALBUM#${photo.albumId}`,
      sk: `PHOTO#${photo.photoId}`,
      ...photo,
    },
  }));

  // Update album photo count
  await updateAlbumPhotoCount(photo.userId, photo.albumId, 1);
}

export async function getPhoto(albumId: string, photoId: string): Promise<Photo | null> {
  const client = getDocClient();

  const response = await client.send(new GetCommand({
    TableName: PHOTOS_TABLE,
    Key: {
      pk: `ALBUM#${albumId}`,
      sk: `PHOTO#${photoId}`,
    },
  }));

  if (!response.Item) return null;

  const { pk, sk, ...photo } = response.Item;
  return photo as Photo;
}

export async function listAlbumPhotos(albumId: string): Promise<Photo[]> {
  const client = getDocClient();

  const response = await client.send(new QueryCommand({
    TableName: PHOTOS_TABLE,
    IndexName: 'albumId-uploadDate-index',
    KeyConditionExpression: 'albumId = :albumId',
    ExpressionAttributeValues: {
      ':albumId': albumId,
    },
    ScanIndexForward: false, // Most recent first
  }));

  return (response.Items || []).map(item => {
    const { pk, sk, ...photo } = item;
    return photo as Photo;
  });
}

// Share link operations
export async function createShareLink(
  albumId: string,
  userId: string,
  expiresInDays?: number
): Promise<ShareLink> {
  const client = getDocClient();
  const linkId = nanoid(16);
  const now = new Date();

  const shareLink: ShareLink = {
    linkId,
    albumId,
    userId,
    createdAt: now.toISOString(),
    accessCount: 0,
    createdBy: userId,
  };

  if (expiresInDays) {
    const expiresAt = new Date(now);
    expiresAt.setDate(expiresAt.getDate() + expiresInDays);
    shareLink.expiresAt = expiresAt.toISOString();
  }

  await client.send(new PutCommand({
    TableName: SHARE_LINKS_TABLE,
    Item: shareLink,
  }));

  return shareLink;
}

export async function getShareLink(linkId: string): Promise<ShareLink | null> {
  const client = getDocClient();

  const response = await client.send(new GetCommand({
    TableName: SHARE_LINKS_TABLE,
    Key: { linkId },
  }));

  if (!response.Item) return null;

  return response.Item as ShareLink;
}

export async function incrementShareLinkAccess(linkId: string): Promise<void> {
  const client = getDocClient();

  await client.send(new UpdateCommand({
    TableName: SHARE_LINKS_TABLE,
    Key: { linkId },
    UpdateExpression: 'SET accessCount = accessCount + :inc',
    ExpressionAttributeValues: {
      ':inc': 1,
    },
  }));
}

export async function deleteShareLink(linkId: string): Promise<void> {
  const client = getDocClient();

  await client.send(new DeleteCommand({
    TableName: SHARE_LINKS_TABLE,
    Key: { linkId },
  }));
}

export async function isShareLinkValid(shareLink: ShareLink): Promise<boolean> {
  if (!shareLink.expiresAt) return true;
  return new Date(shareLink.expiresAt) > new Date();
}

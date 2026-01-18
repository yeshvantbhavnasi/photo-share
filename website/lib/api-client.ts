/**
 * API Client for Family Photo Sharing
 *
 * Fetches data from the Lambda API backed by DynamoDB.
 */

import { PhotoItem, AlbumItem, ShareLinkItem } from './types';

// API Gateway endpoint
const API_ENDPOINT = 'https://yd3tspcwml.execute-api.us-east-1.amazonaws.com/prod';
const CLOUDFRONT_URL = process.env.NEXT_PUBLIC_CLOUDFRONT_URL || 'https://d1nf5k4wr11svj.cloudfront.net';

// Response types from API
interface AlbumResponse {
  id: string;
  name: string;
  photoCount: number;
  coverPhoto?: string;
  createdAt: string;
}

interface PhotoResponse {
  id: string;
  filename: string;
  url: string;
  thumbnailUrl?: string;
  uploadDate: string;
  size: number;
  contentType: string;
}

interface AlbumPhotosResponse {
  albumId: string;
  albumName: string;
  photoCount: number;
  photos: PhotoResponse[];
  shareLink?: {
    token: string;
    expiresAt?: string;
    accessCount: number;
  };
}

// Convert API response to internal types
function toAlbumItem(album: AlbumResponse): AlbumItem {
  return {
    id: album.id,
    name: album.name,
    photoCount: album.photoCount,
    coverPhoto: album.coverPhoto,
    createdAt: album.createdAt,
  };
}

function toPhotoItem(photo: PhotoResponse): PhotoItem {
  return {
    id: photo.id,
    filename: photo.filename,
    url: photo.url,
    thumbnailUrl: photo.thumbnailUrl || photo.url,
    uploadDate: photo.uploadDate,
    size: photo.size,
    contentType: photo.contentType,
  };
}

// API Client
export const apiClient = {
  albums: {
    list: async (): Promise<AlbumItem[]> => {
      try {
        const response = await fetch(`${API_ENDPOINT}/albums`);
        if (!response.ok) throw new Error('Failed to fetch albums');
        const data = await response.json();
        return (data.albums || []).map(toAlbumItem);
      } catch (error) {
        console.error('Error fetching albums:', error);
        return [];
      }
    },

    get: async (id: string): Promise<AlbumItem | null> => {
      try {
        const response = await fetch(`${API_ENDPOINT}/album?id=${encodeURIComponent(id)}`);
        if (!response.ok) return null;
        const data: AlbumPhotosResponse = await response.json();
        return {
          id: data.albumId,
          name: data.albumName,
          photoCount: data.photoCount,
          createdAt: '',
        };
      } catch (error) {
        console.error('Error fetching album:', error);
        return null;
      }
    },

    create: async (name: string, description?: string): Promise<AlbumItem> => {
      // For now, albums are created via the upload script
      // This is a placeholder for future web-based album creation
      throw new Error('Album creation via web is not yet implemented. Use the upload script.');
    },

    update: async (id: string, updates: Partial<AlbumItem>): Promise<void> => {
      // Placeholder for future implementation
      throw new Error('Album update via web is not yet implemented.');
    },
  },

  photos: {
    list: async (albumId: string): Promise<PhotoItem[]> => {
      try {
        const response = await fetch(`${API_ENDPOINT}/album?id=${encodeURIComponent(albumId)}`);
        if (!response.ok) throw new Error('Failed to fetch photos');
        const data: AlbumPhotosResponse = await response.json();
        return (data.photos || []).map(toPhotoItem);
      } catch (error) {
        console.error('Error fetching photos:', error);
        return [];
      }
    },

    add: async (albumId: string, photo: PhotoItem): Promise<void> => {
      // Placeholder for future implementation
      throw new Error('Photo upload via web is not yet implemented. Use the upload script.');
    },
  },

  share: {
    validate: async (token: string): Promise<{ album: AlbumItem; photos: PhotoItem[] } | null> => {
      try {
        const response = await fetch(`${API_ENDPOINT}/share?token=${encodeURIComponent(token)}`);
        if (!response.ok) return null;
        const data: AlbumPhotosResponse = await response.json();
        return {
          album: {
            id: data.albumId,
            name: data.albumName,
            photoCount: data.photoCount,
            createdAt: '',
          },
          photos: (data.photos || []).map(toPhotoItem),
        };
      } catch (error) {
        console.error('Error validating share link:', error);
        return null;
      }
    },

    create: async (albumId: string, expiresInDays?: number): Promise<ShareLinkItem> => {
      // Share links are created via the upload script with --share flag
      throw new Error('Share link creation via web is not yet implemented. Use the upload script with --share flag.');
    },

    get: async (token: string): Promise<ShareLinkItem | null> => {
      // Use validate instead
      const result = await apiClient.share.validate(token);
      if (!result) return null;
      return {
        token,
        albumId: result.album.id,
        albumName: result.album.name,
        url: `${CLOUDFRONT_URL}/shared/?token=${token}`,
        createdAt: '',
        accessCount: 0,
      };
    },
  },

  upload: {
    getPresignedUrl: async (
      albumId: string,
      filename: string,
      contentType: string
    ): Promise<{ uploadUrl: string; photoKey: string; thumbnailKey: string }> => {
      // Placeholder for future web upload implementation
      throw new Error('Web upload is not yet implemented. Use the upload script.');
    },
  },
};

// Helper function to build image URLs
export function getImageUrl(key: string): string {
  if (key.startsWith('http')) {
    return key;
  }
  return `${CLOUDFRONT_URL}/${key}`;
}

export default apiClient;

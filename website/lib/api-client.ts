/**
 * API Client for Family Photo Sharing
 *
 * Fetches data from the Lambda API backed by DynamoDB.
 * Includes authentication via Cognito JWT tokens.
 */

import { PhotoItem, AlbumItem, ShareLinkItem, EditOperation, EditParameters, EditResponse, DuplicateResult } from './types';

// API Gateway endpoint
const API_ENDPOINT = 'https://yd3tspcwml.execute-api.us-east-1.amazonaws.com/prod';
const CLOUDFRONT_URL = process.env.NEXT_PUBLIC_CLOUDFRONT_URL || 'https://d1nf5k4wr11svj.cloudfront.net';

// Auth token getter - will be set by AuthProvider
let getAuthToken: (() => Promise<string | null>) | null = null;

export function setAuthTokenGetter(getter: () => Promise<string | null>) {
  getAuthToken = getter;
}

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

// Authenticated fetch wrapper
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  // Add auth token if available
  if (getAuthToken) {
    const token = await getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  return fetch(url, {
    ...options,
    headers,
  });
}

// API Client
export const apiClient = {
  albums: {
    list: async (): Promise<AlbumItem[]> => {
      try {
        const response = await fetchWithAuth(`${API_ENDPOINT}/albums`);
        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Authentication required');
          }
          throw new Error('Failed to fetch albums');
        }
        const data = await response.json();
        return (data.albums || []).map(toAlbumItem);
      } catch (error) {
        console.error('Error fetching albums:', error);
        throw error;
      }
    },

    get: async (id: string): Promise<AlbumItem | null> => {
      try {
        const response = await fetchWithAuth(`${API_ENDPOINT}/album?id=${encodeURIComponent(id)}`);
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

    create: async (name: string): Promise<AlbumItem> => {
      const response = await fetchWithAuth(`${API_ENDPOINT}/albums`, {
        method: 'POST',
        body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to create album');
      }
      const data = await response.json();
      return toAlbumItem({
        id: data.id,
        name: data.name,
        photoCount: 0,
        createdAt: new Date().toISOString(),
      });
    },

    update: async (id: string, updates: { name?: string }): Promise<{ albumId: string; updated: boolean; name?: string }> => {
      const response = await fetchWithAuth(`${API_ENDPOINT}/album`, {
        method: 'PUT',
        body: JSON.stringify({ albumId: id, ...updates }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to update album');
      }
      return response.json();
    },
  },

  photos: {
    list: async (albumId: string): Promise<PhotoItem[]> => {
      try {
        const response = await fetchWithAuth(`${API_ENDPOINT}/album?id=${encodeURIComponent(albumId)}`);
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

    edit: async (
      photoId: string,
      operation: EditOperation,
      parameters: EditParameters = {}
    ): Promise<EditResponse> => {
      const response = await fetchWithAuth(`${API_ENDPOINT}/edit`, {
        method: 'POST',
        body: JSON.stringify({ photoId, operation, parameters }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Edit failed');
      }
      return response.json();
    },

    rotate: async (photoId: string, angle: 90 | 180 | 270): Promise<EditResponse> => {
      return apiClient.photos.edit(photoId, 'rotate', { angle });
    },

    enhance: async (photoId: string): Promise<EditResponse> => {
      return apiClient.photos.edit(photoId, 'enhance', {});
    },

    upscale: async (photoId: string, scale: 2 | 4 = 2): Promise<EditResponse> => {
      return apiClient.photos.edit(photoId, 'upscale', { scale });
    },

    removeBackground: async (photoId: string): Promise<EditResponse> => {
      return apiClient.photos.edit(photoId, 'remove_bg', {});
    },

    styleTransfer: async (photoId: string, style: EditParameters['style']): Promise<EditResponse> => {
      return apiClient.photos.edit(photoId, 'style_transfer', { style });
    },

    hide: async (photoId: string): Promise<{ photoId: string; hidden: boolean }> => {
      const response = await fetchWithAuth(`${API_ENDPOINT}/photos/${encodeURIComponent(photoId)}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to hide photo');
      }
      return response.json();
    },

    delete: async (photoId: string): Promise<{ photoId: string; hidden: boolean }> => {
      // Alias for hide - soft delete
      return apiClient.photos.hide(photoId);
    },
  },

  share: {
    validate: async (token: string): Promise<{ album: AlbumItem; photos: PhotoItem[] } | null> => {
      try {
        // Share validation does NOT require auth - uses regular fetch
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
      const response = await fetchWithAuth(`${API_ENDPOINT}/share`, {
        method: 'POST',
        body: JSON.stringify({ albumId, expiresInDays }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to create share link');
      }
      const data = await response.json();
      return {
        token: data.token,
        albumId: data.albumId,
        albumName: '',
        url: data.shareUrl,
        createdAt: '',
        expiresAt: data.expiresAt,
        accessCount: 0,
      };
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

  migrate: {
    fromDefaultUser: async (): Promise<{ migratedCount: number; fromUser: string; toUser: string }> => {
      const response = await fetchWithAuth(`${API_ENDPOINT}/migrate`, {
        method: 'POST',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Migration failed');
      }
      return response.json();
    },
  },

  duplicates: {
    findInAlbum: async (albumId: string): Promise<DuplicateResult> => {
      const response = await fetchWithAuth(`${API_ENDPOINT}/duplicates?albumId=${encodeURIComponent(albumId)}`);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Duplicate detection failed');
      }
      return response.json();
    },

    findAcrossAlbums: async (): Promise<DuplicateResult> => {
      const response = await fetchWithAuth(`${API_ENDPOINT}/duplicates`);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Duplicate detection failed');
      }
      return response.json();
    },
  },

  timeline: {
    get: async (options?: { startDate?: string; endDate?: string; limit?: number }): Promise<{
      photos: PhotoItem[];
      byDate: Record<string, PhotoItem[]>;
      totalCount: number;
      hasMore: boolean;
    }> => {
      try {
        const params = new URLSearchParams();
        if (options?.startDate) params.set('startDate', options.startDate);
        if (options?.endDate) params.set('endDate', options.endDate);
        if (options?.limit) params.set('limit', options.limit.toString());

        const url = `${API_ENDPOINT}/timeline${params.toString() ? '?' + params.toString() : ''}`;
        const response = await fetchWithAuth(url);
        if (!response.ok) throw new Error('Failed to fetch timeline');
        const data = await response.json();

        return {
          photos: (data.photos || []).map(toPhotoItem),
          byDate: Object.fromEntries(
            Object.entries(data.byDate || {}).map(([date, photos]) => [
              date,
              (photos as PhotoResponse[]).map(toPhotoItem),
            ])
          ),
          totalCount: data.totalCount || 0,
          hasMore: data.hasMore || false,
        };
      } catch (error) {
        console.error('Error fetching timeline:', error);
        throw error;
      }
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

// Download helper (frontend-only, no API call needed)
export function downloadPhoto(url: string, filename: string): void {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.target = '_blank';
  // Set crossOrigin to allow downloading from CloudFront
  link.setAttribute('crossorigin', 'anonymous');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export default apiClient;

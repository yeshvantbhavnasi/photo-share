export interface PhotoItem {
  id: string;
  filename?: string;
  url: string;
  thumbnailUrl: string;
  uploadDate?: string;
  size?: number;
  contentType?: string;
}

export interface AlbumItem {
  id: string;
  name: string;
  description?: string;
  coverPhoto?: string;
  photoCount: number;
  createdAt: string;
}

export interface ShareLinkItem {
  token: string;
  albumId: string;
  albumName: string;
  url: string;
  createdAt: string;
  expiresAt?: string;
  accessCount: number;
}

export interface UploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'generating-thumbnail' | 'complete' | 'error';
  error?: string;
}

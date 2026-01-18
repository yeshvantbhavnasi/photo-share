export interface PhotoItem {
  id: string;
  src: string;
  thumbnailSrc: string;
  alt: string;
  width?: number;
  height?: number;
}

export interface AlbumItem {
  id: string;
  name: string;
  description?: string;
  coverSrc?: string;
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

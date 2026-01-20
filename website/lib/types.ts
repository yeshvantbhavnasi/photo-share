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

// Image editing types
export type EditOperation = 'rotate' | 'enhance' | 'upscale' | 'remove_bg' | 'style_transfer';

export type StyleType = 'watercolor' | 'oil_painting' | 'sketch' | 'anime' | 'pop_art' | 'impressionist';

export interface EditParameters {
  angle?: 90 | 180 | 270;
  scale?: 2 | 4;
  style?: StyleType;
  brightness?: number;
  contrast?: number;
  saturation?: number;
}

export interface EditedPhotoItem extends PhotoItem {
  editOperation?: string;
  originalPhotoId?: string;
}

export interface EditRequest {
  photoId: string;
  operation: EditOperation;
  parameters?: EditParameters;
}

export interface EditResponse extends PhotoItem {
  editOperation: string;
  originalPhotoId: string;
}

// Duplicate detection types
export interface DuplicatePhoto extends PhotoItem {
  albumId?: string;
  albumName?: string;
  similarity: number;
  exactMatch: boolean;
}

export interface DuplicateGroup {
  photos: DuplicatePhoto[];
  count: number;
  crossAlbum?: boolean;
  albums?: string[];
}

export interface DuplicateResult {
  duplicateGroups: DuplicateGroup[];
  totalPhotos: number;
  duplicatesFound: number;
  groupsFound: number;
  crossAlbumGroups?: number;
}

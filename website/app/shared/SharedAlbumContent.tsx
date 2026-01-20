'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Gallery from '@/components/Gallery';
import { PhotoItem, AlbumItem } from '@/lib/types';
import { apiClient } from '@/lib/api-client';

export default function SharedAlbumContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';

  const [album, setAlbum] = useState<AlbumItem | null>(null);
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError('Invalid share link.');
      setIsLoading(false);
      return;
    }

    const loadSharedAlbum = async () => {
      try {
        const result = await apiClient.share.validate(token);
        if (result) {
          setAlbum(result.album);
          setPhotos(result.photos);
        } else {
          setError('Invalid or expired share link.');
        }
      } catch (err) {
        console.error('Error loading shared album:', err);
        setError('Failed to load shared album.');
      } finally {
        setIsLoading(false);
      }
    };

    loadSharedAlbum();
  }, [token]);

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto animate-pulse">
        <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-64 mb-4" />
        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-48 mb-8" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="aspect-square bg-slate-200 dark:bg-slate-700 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <svg className="w-20 h-20 mx-auto mb-6 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Unable to Load Album</h1>
        <p className="text-slate-600 dark:text-slate-300">{error}</p>
      </div>
    );
  }

  if (!album) return null;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full text-sm mb-4">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
          Shared Album
        </div>

        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white mb-2">{album.name}</h1>
        <p className="text-slate-600 dark:text-slate-300">{photos.length} photo{photos.length !== 1 ? 's' : ''} in this album</p>
      </div>

      {photos.length > 0 ? (
        <Gallery photos={photos} />
      ) : (
        <div className="text-center py-16 bg-slate-50 dark:bg-slate-800 rounded-xl">
          <svg className="w-16 h-16 mx-auto mb-4 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-lg text-slate-600 dark:text-slate-300">No photos in this album yet</p>
        </div>
      )}

      <div className="mt-12 pt-8 border-t border-slate-200 dark:border-slate-700 text-center">
        <p className="text-sm text-slate-500 dark:text-slate-400">Shared via Bhavnasi Share</p>
      </div>
    </div>
  );
}

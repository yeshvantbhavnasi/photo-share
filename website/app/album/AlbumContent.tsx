'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Gallery from '@/components/Gallery';
import ShareButton from '@/components/ShareButton';
import { PhotoItem, AlbumItem } from '@/lib/types';
import { apiClient } from '@/lib/api-client';

export default function AlbumContent() {
  const searchParams = useSearchParams();
  const albumId = searchParams.get('id') || '';

  const [album, setAlbum] = useState<AlbumItem | null>(null);
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!albumId) {
      setIsLoading(false);
      return;
    }

    const loadAlbumData = async () => {
      try {
        // Fetch album and photos from API
        const [albumData, photosData] = await Promise.all([
          apiClient.albums.get(albumId),
          apiClient.photos.list(albumId),
        ]);

        if (albumData) {
          setAlbum(albumData);
        }
        setPhotos(photosData);
      } catch (error) {
        console.error('Failed to load album:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadAlbumData();
  }, [albumId]);

  if (!albumId) {
    return (
      <div className="text-center py-16">
        <p className="text-slate-600 dark:text-slate-300">No album specified.</p>
        <Link href="/albums/" className="text-primary-600 hover:text-primary-700 mt-4 inline-block">
          View all albums
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-64 mb-4" />
        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-32 mb-8" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="aspect-square bg-slate-200 dark:bg-slate-700 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!album) {
    return (
      <div className="text-center py-16">
        <svg className="w-20 h-20 mx-auto mb-6 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">Album not found</h2>
        <p className="text-slate-600 dark:text-slate-300 mb-6">This album may have been deleted or doesn't exist.</p>
        <Link href="/albums/" className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors">
          Back to Albums
        </Link>
      </div>
    );
  }

  return (
    <div>
      <nav className="mb-4 text-sm">
        <Link href="/albums/" className="text-primary-600 hover:text-primary-700 dark:text-primary-400">Albums</Link>
        <span className="mx-2 text-slate-400">/</span>
        <span className="text-slate-600 dark:text-slate-300">{album.name}</span>
      </nav>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">{album.name}</h1>
          {album.description && <p className="text-slate-600 dark:text-slate-300 mt-1">{album.description}</p>}
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
            {photos.length} photo{photos.length !== 1 ? 's' : ''}
            {album.createdAt && ` · Created ${new Date(album.createdAt).toLocaleDateString()}`}
          </p>
        </div>

        <div className="flex gap-3">
          <ShareButton albumId={album.id} albumName={album.name} />
        </div>
      </div>

      <Gallery photos={photos} />
    </div>
  );
}

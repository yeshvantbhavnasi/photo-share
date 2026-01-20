'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import Gallery from '@/components/Gallery';
import AlbumCard from '@/components/AlbumCard';
import MigrationPrompt from '@/components/MigrationPrompt';
import { PhotoItem, AlbumItem } from '@/lib/types';
import { apiClient } from '@/lib/api-client';

export default function HomePage() {
  const [albums, setAlbums] = useState<AlbumItem[]>([]);
  const [recentPhotos, setRecentPhotos] = useState<PhotoItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showMigration, setShowMigration] = useState(false);

  const loadAlbums = useCallback(async () => {
    try {
      const data = await apiClient.albums.list();
      setAlbums(data);
      // Show migration prompt if user has no albums (they might have old data to claim)
      if (data.length === 0) {
        setShowMigration(true);
      }
    } catch (error) {
      console.error('Failed to load albums:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAlbums();
  }, [loadAlbums]);

  const handleMigrationComplete = () => {
    setShowMigration(false);
    setIsLoading(true);
    loadAlbums();
  };

  return (
    <div className="space-y-12">
      {/* Migration Prompt */}
      {showMigration && !isLoading && (
        <MigrationPrompt onMigrationComplete={handleMigrationComplete} />
      )}

      {/* Hero Section */}
      <section className="text-center py-12">
        <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 dark:text-white mb-4">
          Bhavnasi Share
        </h1>
        <p className="text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto mb-8">
          Upload your photos, organize them into albums, and share them with family and friends
          using simple share links.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            href="/upload/"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors font-medium"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            Upload Photos
          </Link>
          <Link
            href="/albums/"
            className="inline-flex items-center gap-2 px-6 py-3 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
          >
            View Albums
          </Link>
        </div>
      </section>

      {/* Recent Albums */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Your Albums</h2>
          <Link
            href="/albums/"
            className="text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
          >
            View all
          </Link>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-slate-100 dark:bg-slate-800 rounded-xl animate-pulse aspect-[4/3]"
              />
            ))}
          </div>
        ) : albums.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {albums.slice(0, 6).map((album) => (
              <AlbumCard key={album.id} album={album} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-slate-50 dark:bg-slate-800 rounded-xl">
            <svg
              className="w-16 h-16 mx-auto mb-4 text-slate-300 dark:text-slate-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
            <p className="text-lg text-slate-600 dark:text-slate-300 mb-4">No albums yet</p>
            <Link
              href="/upload/"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
            >
              Create your first album
            </Link>
          </div>
        )}
      </section>

      {/* Recent Photos */}
      {recentPhotos.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">Recent Photos</h2>
          <Gallery photos={recentPhotos.slice(0, 12)} />
        </section>
      )}

      {/* How it works */}
      <section className="py-12">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-8 text-center">
          How It Works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-primary-600 dark:text-primary-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
              1. Upload Photos
            </h3>
            <p className="text-slate-600 dark:text-slate-300">
              Drag and drop your photos or use our upload tool. We'll automatically create
              thumbnails for fast browsing.
            </p>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-primary-600 dark:text-primary-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
              2. Organize Albums
            </h3>
            <p className="text-slate-600 dark:text-slate-300">
              Create albums for different events or occasions. Keep your memories organized and easy
              to find.
            </p>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-primary-600 dark:text-primary-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
              3. Share with Family
            </h3>
            <p className="text-slate-600 dark:text-slate-300">
              Generate shareable links for your albums. No login required for viewers - just click
              and enjoy!
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

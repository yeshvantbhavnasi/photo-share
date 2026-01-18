'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import UploadDropzone from '@/components/UploadDropzone';
import { AlbumItem } from '@/lib/types';

export default function UploadPage() {
  const router = useRouter();
  const [albums, setAlbums] = useState<AlbumItem[]>([]);
  const [selectedAlbum, setSelectedAlbum] = useState<string>('');
  const [newAlbumName, setNewAlbumName] = useState('');
  const [createNewAlbum, setCreateNewAlbum] = useState(false);
  const [uploadCount, setUploadCount] = useState(0);

  useEffect(() => {
    const storedAlbums = localStorage.getItem('photo-share-albums');
    if (storedAlbums) {
      try {
        const parsed = JSON.parse(storedAlbums);
        setAlbums(parsed);
        if (parsed.length > 0) {
          setSelectedAlbum(parsed[0].id);
        } else {
          setCreateNewAlbum(true);
        }
      } catch {
        setCreateNewAlbum(true);
      }
    } else {
      setCreateNewAlbum(true);
    }
  }, []);

  const handleCreateAndSelect = () => {
    if (!newAlbumName.trim()) return;

    const newAlbum: AlbumItem = {
      id: `album-${Date.now()}`,
      name: newAlbumName.trim(),
      photoCount: 0,
      createdAt: new Date().toISOString(),
    };

    const updatedAlbums = [...albums, newAlbum];
    setAlbums(updatedAlbums);
    localStorage.setItem('photo-share-albums', JSON.stringify(updatedAlbums));

    setSelectedAlbum(newAlbum.id);
    setCreateNewAlbum(false);
    setNewAlbumName('');
  };

  const handleUploadComplete = () => {
    setUploadCount((c) => c + 1);
  };

  const currentAlbum = albums.find((a) => a.id === selectedAlbum);

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Upload Photos</h1>
      <p className="text-slate-600 dark:text-slate-300 mb-8">
        Select an album or create a new one, then upload your photos.
      </p>

      {/* Album Selection */}
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm mb-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          Choose Album
        </h2>

        {!createNewAlbum ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                Select existing album
              </label>
              <select
                value={selectedAlbum}
                onChange={(e) => setSelectedAlbum(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              >
                {albums.map((album) => (
                  <option key={album.id} value={album.id}>
                    {album.name} ({album.photoCount} photos)
                  </option>
                ))}
              </select>
            </div>

            <div className="text-center">
              <span className="text-slate-400">or</span>
            </div>

            <button
              onClick={() => setCreateNewAlbum(true)}
              className="w-full py-2 px-4 border border-dashed border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              + Create new album
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                New album name
              </label>
              <input
                type="text"
                value={newAlbumName}
                onChange={(e) => setNewAlbumName(e.target.value)}
                placeholder="e.g., Vacation 2024"
                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400"
                autoFocus
              />
            </div>

            <div className="flex gap-3">
              {albums.length > 0 && (
                <button
                  onClick={() => setCreateNewAlbum(false)}
                  className="flex-1 py-2 px-4 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
              )}
              <button
                onClick={handleCreateAndSelect}
                disabled={!newAlbumName.trim()}
                className="flex-1 py-2 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white rounded-lg transition-colors"
              >
                Create Album
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Upload Area */}
      {selectedAlbum && !createNewAlbum && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Upload to "{currentAlbum?.name}"
            </h2>
            {uploadCount > 0 && (
              <span className="text-sm text-green-600 dark:text-green-400">
                {uploadCount} uploaded
              </span>
            )}
          </div>

          <UploadDropzone albumId={selectedAlbum} onUploadComplete={handleUploadComplete} />

          {uploadCount > 0 && (
            <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={() => router.push(`/albums/${selectedAlbum}/`)}
                className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
              >
                View Album
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

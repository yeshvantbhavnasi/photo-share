'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { apiClient } from '@/lib/api-client';
import { DuplicateResult, DuplicateGroup, DuplicatePhoto } from '@/lib/types';

export default function DuplicatesPage() {
  const [result, setResult] = useState<DuplicateResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedForDeletion, setSelectedForDeletion] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteProgress, setDeleteProgress] = useState({ current: 0, total: 0 });

  const scanForDuplicates = async () => {
    setIsLoading(true);
    setError(null);
    setSelectedForDeletion(new Set());

    try {
      const data = await apiClient.duplicates.findAcrossAlbums();
      setResult(data);

      // Auto-select all duplicates (keep first photo in each group)
      const duplicatesToDelete = new Set<string>();
      data.duplicateGroups.forEach(group => {
        // Skip the first photo (original), select the rest for deletion
        group.photos.slice(1).forEach(photo => {
          duplicatesToDelete.add(photo.id);
        });
      });
      setSelectedForDeletion(duplicatesToDelete);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to scan for duplicates');
    } finally {
      setIsLoading(false);
    }
  };

  const togglePhotoSelection = (photoId: string) => {
    setSelectedForDeletion(prev => {
      const newSet = new Set(prev);
      if (newSet.has(photoId)) {
        newSet.delete(photoId);
      } else {
        newSet.add(photoId);
      }
      return newSet;
    });
  };

  const selectAllDuplicates = () => {
    if (!result) return;

    const duplicatesToDelete = new Set<string>();
    result.duplicateGroups.forEach(group => {
      group.photos.slice(1).forEach(photo => {
        duplicatesToDelete.add(photo.id);
      });
    });
    setSelectedForDeletion(duplicatesToDelete);
  };

  const deselectAll = () => {
    setSelectedForDeletion(new Set());
  };

  const deleteSelected = async () => {
    if (selectedForDeletion.size === 0) return;

    const confirmDelete = window.confirm(
      `Are you sure you want to delete ${selectedForDeletion.size} duplicate photo${selectedForDeletion.size === 1 ? '' : 's'}? This action cannot be undone.`
    );

    if (!confirmDelete) return;

    setIsDeleting(true);
    setDeleteProgress({ current: 0, total: selectedForDeletion.size });

    const photoIds = Array.from(selectedForDeletion);
    let deletedCount = 0;
    const errors: string[] = [];

    for (const photoId of photoIds) {
      try {
        await apiClient.photos.delete(photoId);
        deletedCount++;
        setDeleteProgress({ current: deletedCount, total: photoIds.length });
      } catch (err) {
        errors.push(photoId);
      }
    }

    setIsDeleting(false);

    if (errors.length > 0) {
      setError(`Deleted ${deletedCount} photos. Failed to delete ${errors.length} photos.`);
    }

    // Refresh the scan
    await scanForDuplicates();
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Find Duplicates</h1>
          <p className="text-slate-600 dark:text-slate-300 mt-1">
            Scan your photos to find and remove duplicates
          </p>
        </div>

        <button
          onClick={scanForDuplicates}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg transition-colors"
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Scanning...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Scan for Duplicates
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {!result && !isLoading && (
        <div className="text-center py-16 bg-slate-50 dark:bg-slate-800 rounded-xl">
          <svg className="w-20 h-20 mx-auto mb-6 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">Ready to Scan</h2>
          <p className="text-slate-600 dark:text-slate-300 mb-6 max-w-md mx-auto">
            Click the button above to scan all your albums for duplicate photos.
            This may take a few moments depending on how many photos you have.
          </p>
        </div>
      )}

      {result && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
            <div className="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-500 dark:text-slate-400">Total Photos</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{result.totalPhotos}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-500 dark:text-slate-400">Duplicate Groups</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{result.groupsFound}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-500 dark:text-slate-400">Duplicates Found</p>
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">{result.duplicatesFound}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
              <p className="text-sm text-slate-500 dark:text-slate-400">Selected for Deletion</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">{selectedForDeletion.size}</p>
            </div>
          </div>

          {result.duplicatesFound > 0 && (
            <>
              {/* Action Bar */}
              <div className="flex flex-wrap items-center gap-3 mb-6 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <button
                  onClick={selectAllDuplicates}
                  className="px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Select All Duplicates
                </button>
                <button
                  onClick={deselectAll}
                  className="px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Deselect All
                </button>
                <div className="flex-1" />
                <button
                  onClick={deleteSelected}
                  disabled={selectedForDeletion.size === 0 || isDeleting}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white font-medium rounded-lg transition-colors"
                >
                  {isDeleting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                      Deleting {deleteProgress.current}/{deleteProgress.total}...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Delete Selected ({selectedForDeletion.size})
                    </>
                  )}
                </button>
              </div>

              {/* Duplicate Groups */}
              <div className="space-y-6">
                {result.duplicateGroups.map((group, groupIndex) => (
                  <DuplicateGroupCard
                    key={groupIndex}
                    group={group}
                    groupIndex={groupIndex}
                    selectedForDeletion={selectedForDeletion}
                    onToggleSelection={togglePhotoSelection}
                  />
                ))}
              </div>
            </>
          )}

          {result.duplicatesFound === 0 && (
            <div className="text-center py-16 bg-green-50 dark:bg-green-900/30 rounded-xl">
              <svg className="w-20 h-20 mx-auto mb-6 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h2 className="text-xl font-semibold text-green-800 dark:text-green-200 mb-2">No Duplicates Found</h2>
              <p className="text-green-700 dark:text-green-300">
                Great news! We didn't find any duplicate photos across your albums.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

interface DuplicateGroupCardProps {
  group: DuplicateGroup;
  groupIndex: number;
  selectedForDeletion: Set<string>;
  onToggleSelection: (photoId: string) => void;
}

function DuplicateGroupCard({ group, groupIndex, selectedForDeletion, onToggleSelection }: DuplicateGroupCardProps) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-white">
            Group {groupIndex + 1}
            <span className="ml-2 text-sm font-normal text-slate-500 dark:text-slate-400">
              ({group.count} photos)
            </span>
          </h3>
          {group.crossAlbum && (
            <p className="text-sm text-orange-600 dark:text-orange-400 mt-0.5">
              Duplicates across multiple albums
            </p>
          )}
        </div>
      </div>

      <div className="p-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {group.photos.map((photo, photoIndex) => (
            <div
              key={photo.id}
              className={`relative group cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                selectedForDeletion.has(photo.id)
                  ? 'border-red-500 ring-2 ring-red-500/30'
                  : photoIndex === 0
                  ? 'border-green-500 ring-2 ring-green-500/30'
                  : 'border-transparent hover:border-slate-300 dark:hover:border-slate-600'
              }`}
              onClick={() => photoIndex > 0 && onToggleSelection(photo.id)}
            >
              <div className="aspect-square relative bg-slate-100 dark:bg-slate-700">
                <Image
                  src={photo.thumbnailUrl || photo.url}
                  alt={photo.filename || `Photo ${photo.id}`}
                  fill
                  sizes="(max-width: 640px) 50vw, (max-width: 1024px) 25vw, 20vw"
                  className="object-cover"
                />

                {/* Original badge */}
                {photoIndex === 0 && (
                  <div className="absolute top-2 left-2 px-2 py-0.5 bg-green-500 text-white text-xs font-medium rounded">
                    Keep
                  </div>
                )}

                {/* Selected for deletion */}
                {selectedForDeletion.has(photo.id) && (
                  <div className="absolute inset-0 bg-red-500/30 flex items-center justify-center">
                    <div className="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </div>
                  </div>
                )}

                {/* Similarity badge */}
                {photoIndex > 0 && !selectedForDeletion.has(photo.id) && (
                  <div className={`absolute top-2 right-2 px-2 py-0.5 text-xs font-medium rounded ${
                    photo.exactMatch
                      ? 'bg-red-500 text-white'
                      : 'bg-orange-500 text-white'
                  }`}>
                    {photo.exactMatch ? 'Exact' : `${photo.similarity}%`}
                  </div>
                )}
              </div>

              {/* Photo info */}
              <div className="p-2 bg-slate-50 dark:bg-slate-700/50">
                <p className="text-xs text-slate-600 dark:text-slate-400 truncate">
                  {photo.filename || photo.id}
                </p>
                {photo.albumName && (
                  <p className="text-xs text-slate-500 dark:text-slate-500 truncate">
                    {photo.albumName}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

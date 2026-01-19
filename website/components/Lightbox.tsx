'use client';

import { useEffect, useCallback, useState } from 'react';
import Image from 'next/image';
import { PhotoItem } from '@/lib/types';
import { downloadPhoto, apiClient } from '@/lib/api-client';
import EditModal from './EditModal';

interface LightboxProps {
  photos: PhotoItem[];
  currentIndex: number;
  onClose: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onPhotoAdded?: (photo: PhotoItem) => void;
  onPhotoDeleted?: (photoId: string) => void;
}

export default function Lightbox({
  photos,
  currentIndex,
  onClose,
  onNext,
  onPrevious,
  onPhotoAdded,
  onPhotoDeleted,
}: LightboxProps) {
  const currentPhoto = photos[currentIndex];
  const [isRotating, setIsRotating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (showEditModal || showDeleteConfirm) return; // Don't handle keys when modal is open

      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowRight':
          onNext();
          break;
        case 'ArrowLeft':
          onPrevious();
          break;
        case 'd':
        case 'D':
          handleDownload();
          break;
        case 'Delete':
        case 'Backspace':
          setShowDeleteConfirm(true);
          break;
      }
    },
    [onClose, onNext, onPrevious, showEditModal, showDeleteConfirm]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [handleKeyDown]);

  const handleDownload = () => {
    const filename = currentPhoto.filename || `photo-${currentPhoto.id}.jpg`;
    downloadPhoto(currentPhoto.url, filename);
  };

  const handleRotate = async (angle: 90 | 270) => {
    if (isRotating) return;

    setIsRotating(true);
    try {
      const result = await apiClient.photos.rotate(currentPhoto.id, angle);
      if (onPhotoAdded) {
        onPhotoAdded(result);
      }
    } catch (error) {
      console.error('Rotation failed:', error);
      alert('Failed to rotate image. Please try again.');
    } finally {
      setIsRotating(false);
    }
  };

  const handleDelete = async () => {
    if (isDeleting) return;

    setIsDeleting(true);
    try {
      await apiClient.photos.hide(currentPhoto.id);
      setShowDeleteConfirm(false);
      if (onPhotoDeleted) {
        onPhotoDeleted(currentPhoto.id);
      }
      // If this was the last photo, close the lightbox
      if (photos.length === 1) {
        onClose();
      }
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to hide photo. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleEditSave = (newPhoto: PhotoItem) => {
    if (onPhotoAdded) {
      onPhotoAdded(newPhoto);
    }
    setShowEditModal(false);
  };

  return (
    <>
      <div
        className="lightbox-overlay fixed inset-0 z-50 bg-black/95 flex flex-col"
        onClick={onClose}
      >
        {/* Top toolbar */}
        <div
          className="flex items-center justify-between px-4 py-3 bg-black/50"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Left side - photo info */}
          <div className="text-white/70 text-sm">
            {currentPhoto.filename && (
              <span className="mr-4">{currentPhoto.filename}</span>
            )}
            <span>{currentIndex + 1} / {photos.length}</span>
          </div>

          {/* Right side - action buttons */}
          <div className="flex items-center gap-2">
            {/* Rotate Left */}
            <button
              onClick={() => handleRotate(270)}
              disabled={isRotating}
              className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
              title="Rotate left (saves as new photo)"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 10h1.5a4.5 4.5 0 014.5 4.5V15m-6-5l3-3m-3 3l3 3M21 14h-1.5a4.5 4.5 0 00-4.5 4.5V19"
                />
              </svg>
            </button>

            {/* Rotate Right */}
            <button
              onClick={() => handleRotate(90)}
              disabled={isRotating}
              className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
              title="Rotate right (saves as new photo)"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 10h-1.5a4.5 4.5 0 00-4.5 4.5V15m6-5l-3-3m3 3l-3 3M3 14h1.5a4.5 4.5 0 014.5 4.5V19"
                />
              </svg>
            </button>

            {/* Divider */}
            <div className="w-px h-6 bg-white/20 mx-1" />

            {/* Download */}
            <button
              onClick={handleDownload}
              className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              title="Download original (D)"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            </button>

            {/* Edit (AI) */}
            <button
              onClick={() => setShowEditModal(true)}
              className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              title="Edit with AI"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </button>

            {/* Divider */}
            <div className="w-px h-6 bg-white/20 mx-1" />

            {/* Delete/Hide */}
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="p-2 text-white/70 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              title="Hide photo (Delete)"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>

            {/* Divider */}
            <div className="w-px h-6 bg-white/20 mx-1" />

            {/* Close */}
            <button
              onClick={onClose}
              className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              title="Close (Esc)"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Main image area */}
        <div className="flex-1 flex items-center justify-center relative">
          {/* Previous button */}
          {photos.length > 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onPrevious();
              }}
              className="absolute left-4 z-10 p-2 text-white/70 hover:text-white transition-colors"
              aria-label="Previous photo"
            >
              <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
          )}

          {/* Image */}
          <div
            className="relative max-w-[90vw] max-h-[calc(100vh-80px)] w-full h-full flex items-center justify-center"
            onClick={(e) => e.stopPropagation()}
          >
            <Image
              src={currentPhoto.url}
              alt={currentPhoto.filename || `Photo ${currentPhoto.id}`}
              fill
              sizes="90vw"
              className="object-contain"
              priority
            />
          </div>

          {/* Next button */}
          {photos.length > 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onNext();
              }}
              className="absolute right-4 z-10 p-2 text-white/70 hover:text-white transition-colors"
              aria-label="Next photo"
            >
              <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          )}
        </div>

        {/* Loading indicator for rotation */}
        {isRotating && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-20">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-4 border-white/30 border-t-white rounded-full animate-spin" />
              <span className="text-white text-sm">Rotating...</span>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div
          className="fixed inset-0 z-[60] bg-black/80 flex items-center justify-center p-4"
          onClick={() => !isDeleting && setShowDeleteConfirm(false)}
        >
          <div
            className="bg-gray-900 rounded-xl max-w-md w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white">Hide Photo</h3>
            </div>

            <p className="text-gray-300 mb-2">
              Are you sure you want to hide this photo?
            </p>
            <p className="text-gray-500 text-sm mb-6">
              The photo will be hidden from the album but can be restored later. The original file will not be deleted from storage.
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Hiding...
                  </>
                ) : (
                  'Hide Photo'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <EditModal
          photo={currentPhoto}
          onClose={() => setShowEditModal(false)}
          onSave={handleEditSave}
        />
      )}
    </>
  );
}

'use client';

import { useEffect, useCallback, useState } from 'react';
import Image from 'next/image';
import { PhotoItem, EditOperation, StyleType } from '@/lib/types';
import { downloadPhoto, apiClient } from '@/lib/api-client';

interface LightboxProps {
  photos: PhotoItem[];
  currentIndex: number;
  onClose: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onPhotoAdded?: (photo: PhotoItem) => void;
  onPhotoDeleted?: (photoId: string) => void;
}

const STYLES: { id: StyleType; name: string }[] = [
  { id: 'watercolor', name: 'Watercolor' },
  { id: 'oil_painting', name: 'Oil Painting' },
  { id: 'sketch', name: 'Pencil Sketch' },
  { id: 'anime', name: 'Anime' },
  { id: 'pop_art', name: 'Pop Art' },
  { id: 'impressionist', name: 'Impressionist' },
];

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
  const [rotation, setRotation] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingOperation, setProcessingOperation] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedStyle, setSelectedStyle] = useState<StyleType>('watercolor');
  const [selectedScale, setSelectedScale] = useState<2 | 4>(2);
  const [showStyleOptions, setShowStyleOptions] = useState(false);

  // Reset state when changing photos
  useEffect(() => {
    setRotation(0);
    setError(null);
    setShowStyleOptions(false);
  }, [currentIndex]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (showDeleteConfirm || isProcessing) return;

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
    [onClose, onNext, onPrevious, showDeleteConfirm, isProcessing]
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

  const handleRotate = (direction: 'left' | 'right') => {
    setRotation((prev) => {
      const delta = direction === 'right' ? 90 : -90;
      return (prev + delta + 360) % 360;
    });
  };

  const handleSaveRotation = async () => {
    if (isProcessing || rotation === 0) return;

    setIsProcessing(true);
    setProcessingOperation('Saving rotation');
    setError(null);
    try {
      const apiAngle = rotation as 90 | 180 | 270;
      const result = await apiClient.photos.rotate(currentPhoto.id, apiAngle);
      if (onPhotoAdded) {
        onPhotoAdded(result);
      }
      setRotation(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save rotation');
    } finally {
      setIsProcessing(false);
      setProcessingOperation(null);
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
      if (photos.length === 1) {
        onClose();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to hide photo');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleAIOperation = async (operation: EditOperation, params?: Record<string, unknown>) => {
    if (isProcessing) return;

    setIsProcessing(true);
    setError(null);

    const operationNames: Record<EditOperation, string> = {
      enhance: 'Enhancing',
      upscale: 'Upscaling',
      remove_bg: 'Removing background',
      style_transfer: 'Applying style',
      rotate: 'Rotating',
    };
    setProcessingOperation(operationNames[operation] || 'Processing');

    try {
      let result: PhotoItem;

      switch (operation) {
        case 'enhance':
          result = await apiClient.photos.enhance(currentPhoto.id);
          break;
        case 'upscale':
          result = await apiClient.photos.upscale(currentPhoto.id, selectedScale);
          break;
        case 'remove_bg':
          result = await apiClient.photos.removeBackground(currentPhoto.id);
          break;
        case 'style_transfer':
          result = await apiClient.photos.styleTransfer(currentPhoto.id, selectedStyle);
          break;
        default:
          throw new Error('Unknown operation');
      }

      if (onPhotoAdded) {
        onPhotoAdded(result);
      }
      setShowStyleOptions(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
    } finally {
      setIsProcessing(false);
      setProcessingOperation(null);
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black flex">
        {/* Main image area */}
        <div className="flex-1 flex flex-col">
          {/* Top bar with photo info */}
          <div className="flex items-center justify-between px-4 py-3 bg-black/50">
            <div className="text-white/70 text-sm">
              {currentPhoto.filename && (
                <span className="mr-4">{currentPhoto.filename}</span>
              )}
              <span>{currentIndex + 1} / {photos.length}</span>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              title="Close (Esc)"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Image with navigation */}
          <div className="flex-1 flex items-center justify-center relative">
            {/* Previous button */}
            {photos.length > 1 && (
              <button
                onClick={onPrevious}
                className="absolute left-4 z-10 p-2 text-white/70 hover:text-white transition-colors"
                aria-label="Previous photo"
              >
                <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            )}

            {/* Image */}
            <div className="relative max-w-[calc(100vw-320px)] max-h-[calc(100vh-80px)] w-full h-full flex items-center justify-center">
              <Image
                src={currentPhoto.url}
                alt={currentPhoto.filename || `Photo ${currentPhoto.id}`}
                fill
                sizes="calc(100vw - 320px)"
                className="object-contain transition-transform duration-200"
                style={{ transform: `rotate(${rotation}deg)` }}
                priority
              />
            </div>

            {/* Next button */}
            {photos.length > 1 && (
              <button
                onClick={onNext}
                className="absolute right-4 z-10 p-2 text-white/70 hover:text-white transition-colors"
                aria-label="Next photo"
              >
                <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            )}

            {/* Processing overlay */}
            {isProcessing && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/70 z-20">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-10 h-10 border-4 border-white/30 border-t-white rounded-full animate-spin" />
                  <span className="text-white text-sm">{processingOperation}...</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right sidebar - Edit panel */}
        <div className="w-80 bg-gray-900 border-l border-gray-800 flex flex-col overflow-hidden">
          {/* Edit panel header */}
          <div className="px-4 py-3 border-b border-gray-800">
            <h2 className="text-lg font-semibold text-white">Edit Photo</h2>
          </div>

          {/* Error message */}
          {error && (
            <div className="mx-4 mt-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg">
              <p className="text-red-200 text-sm">{error}</p>
              <button
                onClick={() => setError(null)}
                className="text-red-400 text-xs hover:text-red-300 mt-1"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Edit options */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Quick actions */}
            <div>
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
                Quick Actions
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleDownload}
                  disabled={isProcessing}
                  className="flex flex-col items-center gap-2 p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span className="text-xs text-gray-300">Download</span>
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={isProcessing}
                  className="flex flex-col items-center gap-2 p-3 bg-gray-800 hover:bg-red-900/50 rounded-lg transition-colors disabled:opacity-50"
                >
                  <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span className="text-xs text-gray-300">Delete</span>
                </button>
              </div>
            </div>

            {/* Rotate */}
            <div>
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
                Rotate
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => handleRotate('left')}
                  disabled={isProcessing}
                  className="flex-1 flex items-center justify-center gap-2 p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  <svg className="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h1.5a4.5 4.5 0 014.5 4.5V15m-6-5l3-3m-3 3l3 3" />
                  </svg>
                  <span className="text-sm text-gray-300">Left</span>
                </button>
                <button
                  onClick={() => handleRotate('right')}
                  disabled={isProcessing}
                  className="flex-1 flex items-center justify-center gap-2 p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  <span className="text-sm text-gray-300">Right</span>
                  <svg className="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10h-1.5a4.5 4.5 0 00-4.5 4.5V15m6-5l-3-3m3 3l-3 3" />
                  </svg>
                </button>
              </div>
              {rotation !== 0 && (
                <button
                  onClick={handleSaveRotation}
                  disabled={isProcessing}
                  className="w-full mt-2 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
                >
                  Save Rotation ({rotation}°)
                </button>
              )}
            </div>

            {/* AI Enhancements */}
            <div>
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
                AI Enhancements
              </h3>
              <div className="space-y-2">
                <button
                  onClick={() => handleAIOperation('enhance')}
                  disabled={isProcessing}
                  className="w-full flex items-center gap-3 p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  <svg className="w-5 h-5 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <div className="text-left">
                    <div className="text-sm font-medium text-white">Auto-Enhance</div>
                    <div className="text-xs text-gray-500">Improve colors & clarity</div>
                  </div>
                </button>

                <button
                  onClick={() => handleAIOperation('remove_bg')}
                  disabled={isProcessing}
                  className="w-full flex items-center gap-3 p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z" />
                  </svg>
                  <div className="text-left">
                    <div className="text-sm font-medium text-white">Remove Background</div>
                    <div className="text-xs text-gray-500">Transparent PNG output</div>
                  </div>
                </button>

                {/* Upscale with options */}
                <div className="bg-gray-800 rounded-lg overflow-hidden">
                  <div className="flex items-center gap-3 p-3">
                    <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                    </svg>
                    <div className="text-left flex-1">
                      <div className="text-sm font-medium text-white">AI Upscale</div>
                      <div className="text-xs text-gray-500">Increase resolution</div>
                    </div>
                  </div>
                  <div className="flex border-t border-gray-700">
                    <button
                      onClick={() => {
                        setSelectedScale(2);
                        handleAIOperation('upscale');
                      }}
                      disabled={isProcessing}
                      className="flex-1 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors disabled:opacity-50 border-r border-gray-700"
                    >
                      2x
                    </button>
                    <button
                      onClick={() => {
                        setSelectedScale(4);
                        handleAIOperation('upscale');
                      }}
                      disabled={isProcessing}
                      className="flex-1 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors disabled:opacity-50"
                    >
                      4x
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Style Transfer */}
            <div>
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
                Artistic Styles
              </h3>
              {showStyleOptions ? (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    {STYLES.map((style) => (
                      <button
                        key={style.id}
                        onClick={() => {
                          setSelectedStyle(style.id);
                          handleAIOperation('style_transfer');
                        }}
                        disabled={isProcessing}
                        className="py-2 px-3 bg-gray-800 hover:bg-purple-900/50 text-sm text-gray-300 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {style.name}
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={() => setShowStyleOptions(false)}
                    className="w-full py-2 text-xs text-gray-500 hover:text-gray-400"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowStyleOptions(true)}
                  disabled={isProcessing}
                  className="w-full flex items-center gap-3 p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  <svg className="w-5 h-5 text-pink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                  </svg>
                  <div className="text-left">
                    <div className="text-sm font-medium text-white">Apply Style</div>
                    <div className="text-xs text-gray-500">Watercolor, Sketch, Anime...</div>
                  </div>
                </button>
              )}
            </div>

            {/* Info notice */}
            <div className="p-3 bg-blue-900/20 rounded-lg border border-blue-800/50">
              <p className="text-xs text-blue-300">
                AI operations create a new photo in your album. Original is preserved.
              </p>
            </div>
          </div>
        </div>
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
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white">Hide Photo</h3>
            </div>

            <p className="text-gray-300 mb-2">
              Are you sure you want to hide this photo?
            </p>
            <p className="text-gray-500 text-sm mb-6">
              The photo will be hidden from the album but can be restored later.
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
    </>
  );
}

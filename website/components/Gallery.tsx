'use client';

import { useState, useCallback, useEffect } from 'react';
import Image from 'next/image';
import { PhotoItem } from '@/lib/types';
import Lightbox from './Lightbox';

interface GalleryProps {
  photos: PhotoItem[];
  showAlbumName?: boolean;
}

export default function Gallery({ photos: initialPhotos, showAlbumName }: GalleryProps) {
  const [photos, setPhotos] = useState<PhotoItem[]>(initialPhotos);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Update local photos when props change
  useEffect(() => {
    setPhotos(initialPhotos);
  }, [initialPhotos]);

  const openLightbox = useCallback((index: number) => {
    setCurrentIndex(index);
    setLightboxOpen(true);
  }, []);

  const closeLightbox = useCallback(() => {
    setLightboxOpen(false);
  }, []);

  const goToNext = useCallback(() => {
    setCurrentIndex((prev) => (prev + 1) % photos.length);
  }, [photos.length]);

  const goToPrevious = useCallback(() => {
    setCurrentIndex((prev) => (prev - 1 + photos.length) % photos.length);
  }, [photos.length]);

  const handlePhotoAdded = useCallback((newPhoto: PhotoItem) => {
    setPhotos((prev) => [...prev, newPhoto]);
  }, []);

  const handlePhotoDeleted = useCallback((photoId: string) => {
    setPhotos((prev) => {
      const newPhotos = prev.filter((p) => p.id !== photoId);
      // Adjust current index if needed
      if (currentIndex >= newPhotos.length && newPhotos.length > 0) {
        setCurrentIndex(newPhotos.length - 1);
      }
      return newPhotos;
    });
  }, [currentIndex]);

  if (photos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-500">
        <svg
          className="w-16 h-16 mb-4 text-slate-300"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        <p className="text-lg">No photos yet</p>
        <p className="text-sm text-slate-400 mt-1">Upload some photos to get started</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 sm:gap-3">
        {photos.map((photo, index) => (
          <div
            key={photo.id}
            className="photo-grid-item relative aspect-square bg-slate-100 dark:bg-slate-800 rounded-lg overflow-hidden cursor-pointer shadow-sm hover:shadow-md"
            onClick={() => openLightbox(index)}
          >
            <Image
              src={photo.thumbnailUrl || photo.url}
              alt={photo.filename || `Photo ${photo.id}`}
              fill
              sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, (max-width: 1024px) 25vw, (max-width: 1280px) 20vw, 16vw"
              className="object-cover"
              loading="lazy"
            />
          </div>
        ))}
      </div>

      {lightboxOpen && (
        <Lightbox
          photos={photos}
          currentIndex={currentIndex}
          onClose={closeLightbox}
          onNext={goToNext}
          onPrevious={goToPrevious}
          onPhotoAdded={handlePhotoAdded}
          onPhotoDeleted={handlePhotoDeleted}
        />
      )}
    </>
  );
}

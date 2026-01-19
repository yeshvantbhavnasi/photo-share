'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import Gallery from '@/components/Gallery';
import Lightbox from '@/components/Lightbox';
import { PhotoItem } from '@/lib/types';

const API_ENDPOINT = 'https://yd3tspcwml.execute-api.us-east-1.amazonaws.com/prod';

interface TimelineResponse {
  photos: PhotoItem[];
  byDate: { [date: string]: PhotoItem[] };
  totalCount: number;
  hasMore: boolean;
  error?: string;
}

export default function TimelinePage() {
  const [timelineData, setTimelineData] = useState<TimelineResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  const fetchTimeline = async (start?: string, end?: string) => {
    setIsLoading(true);
    try {
      let url = `${API_ENDPOINT}/timeline?limit=200`;
      if (start) url += `&startDate=${start}`;
      if (end) url += `&endDate=${end}`;

      const response = await fetch(url);
      const data: TimelineResponse = await response.json();
      setTimelineData(data);
    } catch (error) {
      console.error('Error fetching timeline:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTimeline();
  }, []);

  const handleFilter = () => {
    fetchTimeline(startDate || undefined, endDate || undefined);
  };

  const handleClearFilter = () => {
    setStartDate('');
    setEndDate('');
    fetchTimeline();
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Get sorted dates (newest first)
  const sortedDates = timelineData?.byDate
    ? Object.keys(timelineData.byDate).sort((a, b) => b.localeCompare(a))
    : [];

  // Get all photos for lightbox navigation
  const allPhotos = timelineData?.photos || [];

  const handlePhotoClick = (photo: PhotoItem) => {
    const index = allPhotos.findIndex((p) => p.id === photo.id);
    setSelectedIndex(index);
  };

  const handleCloseLightbox = () => {
    setSelectedIndex(-1);
  };

  const handleNext = () => {
    if (selectedIndex < allPhotos.length - 1) {
      setSelectedIndex(selectedIndex + 1);
    } else {
      setSelectedIndex(0);
    }
  };

  const handlePrevious = () => {
    if (selectedIndex > 0) {
      setSelectedIndex(selectedIndex - 1);
    } else {
      setSelectedIndex(allPhotos.length - 1);
    }
  };

  const handlePhotoAdded = (newPhoto: PhotoItem) => {
    if (timelineData) {
      const date = newPhoto.uploadDate?.substring(0, 10) || new Date().toISOString().substring(0, 10);
      const newPhotos = [...timelineData.photos, newPhoto];
      setTimelineData({
        ...timelineData,
        photos: newPhotos,
        byDate: {
          ...timelineData.byDate,
          [date]: [...(timelineData.byDate[date] || []), newPhoto],
        },
        totalCount: timelineData.totalCount + 1,
      });
      // Navigate to the newly added photo
      setSelectedIndex(newPhotos.length - 1);
    }
  };

  const handlePhotoDeleted = (photoId: string) => {
    if (timelineData) {
      const newPhotos = timelineData.photos.filter((p) => p.id !== photoId);
      const newByDate: { [date: string]: PhotoItem[] } = {};

      for (const [date, photos] of Object.entries(timelineData.byDate)) {
        const filtered = photos.filter((p) => p.id !== photoId);
        if (filtered.length > 0) {
          newByDate[date] = filtered;
        }
      }

      setTimelineData({
        ...timelineData,
        photos: newPhotos,
        byDate: newByDate,
        totalCount: newPhotos.length,
      });

      // Adjust index if needed
      if (selectedIndex >= newPhotos.length && newPhotos.length > 0) {
        setSelectedIndex(newPhotos.length - 1);
      } else if (newPhotos.length === 0) {
        setSelectedIndex(-1);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-48 mb-4" />
          <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-64 mb-8" />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <div key={i} className="aspect-square bg-slate-200 dark:bg-slate-700 rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white mb-2">
          Timeline
        </h1>
        <p className="text-slate-600 dark:text-slate-300">
          {timelineData?.totalCount || 0} photos ordered by date
        </p>
      </div>

      {/* Date Filter */}
      <div className="mb-8 p-4 bg-slate-50 dark:bg-slate-800 rounded-xl">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              From Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              To Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleFilter}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors font-medium"
          >
            Filter
          </button>
          {(startDate || endDate) && (
            <button
              onClick={handleClearFilter}
              className="px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg transition-colors font-medium"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Error State */}
      {timelineData?.error && (
        <div className="mb-8 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl">
          <p className="text-amber-800 dark:text-amber-200">
            Note: Date indexing is still being set up. Please try again in a few minutes.
          </p>
        </div>
      )}

      {/* Timeline View */}
      {sortedDates.length > 0 ? (
        <div className="space-y-12">
          {sortedDates.map((date) => (
            <div key={date} className="relative">
              {/* Date Header */}
              <div className="sticky top-20 z-10 mb-4">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-full shadow-sm">
                  <svg
                    className="w-5 h-5 text-primary-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {formatDate(date)}
                  </span>
                  <span className="text-sm text-slate-500 dark:text-slate-400">
                    ({timelineData?.byDate[date]?.length || 0} photos)
                  </span>
                </div>
              </div>

              {/* Photos Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {timelineData?.byDate[date]?.map((photo) => (
                  <div
                    key={photo.id}
                    className="group relative aspect-square rounded-lg overflow-hidden cursor-pointer bg-slate-100 dark:bg-slate-800"
                    onClick={() => handlePhotoClick(photo)}
                  >
                    <Image
                      src={photo.thumbnailUrl || photo.url}
                      alt={photo.filename || 'Photo'}
                      fill
                      className="object-cover transition-transform group-hover:scale-105"
                      sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, (max-width: 1024px) 25vw, 20vw"
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-slate-50 dark:bg-slate-800 rounded-xl">
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
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p className="text-lg text-slate-600 dark:text-slate-300">
            No photos found for the selected date range
          </p>
        </div>
      )}

      {/* Lightbox */}
      {selectedIndex >= 0 && allPhotos.length > 0 && (
        <Lightbox
          photos={allPhotos}
          currentIndex={selectedIndex}
          onClose={handleCloseLightbox}
          onNext={handleNext}
          onPrevious={handlePrevious}
          onPhotoAdded={handlePhotoAdded}
          onPhotoDeleted={handlePhotoDeleted}
        />
      )}
    </div>
  );
}

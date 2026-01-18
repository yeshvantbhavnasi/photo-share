'use client';

import { Suspense } from 'react';
import SharedAlbumContent from './SharedAlbumContent';

function LoadingState() {
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

export default function SharedAlbumPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <SharedAlbumContent />
    </Suspense>
  );
}

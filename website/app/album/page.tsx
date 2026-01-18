'use client';

import { Suspense } from 'react';
import AlbumContent from './AlbumContent';

function LoadingState() {
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

export default function AlbumViewPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <AlbumContent />
    </Suspense>
  );
}

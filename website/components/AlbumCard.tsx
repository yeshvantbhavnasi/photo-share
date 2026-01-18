'use client';

import Link from 'next/link';
import Image from 'next/image';
import { AlbumItem } from '@/lib/types';

interface AlbumCardProps {
  album: AlbumItem;
}

export default function AlbumCard({ album }: AlbumCardProps) {
  return (
    <Link
      href={`/album/?id=${album.id}`}
      className="group block bg-white dark:bg-slate-800 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all"
    >
      <div className="relative aspect-[4/3] bg-slate-100 dark:bg-slate-700">
        {album.coverSrc ? (
          <Image
            src={album.coverSrc}
            alt={album.name}
            fill
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
            className="object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <svg
              className="w-12 h-12 text-slate-300 dark:text-slate-600"
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
          </div>
        )}
      </div>

      <div className="p-4">
        <h3 className="font-semibold text-slate-900 dark:text-white truncate">{album.name}</h3>
        <div className="flex items-center gap-2 mt-1 text-sm text-slate-500 dark:text-slate-400">
          <span>{album.photoCount} photos</span>
          <span className="text-slate-300 dark:text-slate-600">|</span>
          <span>{new Date(album.createdAt).toLocaleDateString()}</span>
        </div>
        {album.description && (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300 line-clamp-2">
            {album.description}
          </p>
        )}
      </div>
    </Link>
  );
}

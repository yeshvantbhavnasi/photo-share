'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadProgress } from '@/lib/types';

interface UploadDropzoneProps {
  albumId: string;
  onUploadComplete?: (photoId: string) => void;
}

export default function UploadDropzone({ albumId, onUploadComplete }: UploadDropzoneProps) {
  const [uploads, setUploads] = useState<UploadProgress[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const generateThumbnail = async (file: File): Promise<Blob> => {
    return new Promise((resolve, reject) => {
      const img = new window.Image();
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      img.onload = () => {
        const maxSize = 400;
        let { width, height } = img;

        if (width > height) {
          if (width > maxSize) {
            height = (height * maxSize) / width;
            width = maxSize;
          }
        } else {
          if (height > maxSize) {
            width = (width * maxSize) / height;
            height = maxSize;
          }
        }

        canvas.width = width;
        canvas.height = height;
        ctx?.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (blob) resolve(blob);
            else reject(new Error('Failed to generate thumbnail'));
          },
          'image/jpeg',
          0.8
        );
      };

      img.onerror = reject;
      img.src = URL.createObjectURL(file);
    });
  };

  const uploadFile = async (file: File, index: number) => {
    const photoId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    try {
      // Update status to uploading
      setUploads((prev) =>
        prev.map((u, i) => (i === index ? { ...u, status: 'uploading' as const, progress: 10 } : u))
      );

      // Get presigned URL from API
      const presignResponse = await fetch('/api/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          albumId,
          filename: file.name,
          contentType: file.type,
        }),
      });

      if (!presignResponse.ok) {
        throw new Error('Failed to get upload URL');
      }

      const { uploadUrl, photoKey, thumbnailKey } = await presignResponse.json();

      setUploads((prev) =>
        prev.map((u, i) => (i === index ? { ...u, progress: 30 } : u))
      );

      // Upload original photo
      await fetch(uploadUrl, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': file.type },
      });

      setUploads((prev) =>
        prev.map((u, i) =>
          i === index ? { ...u, status: 'generating-thumbnail' as const, progress: 60 } : u
        )
      );

      // Generate and upload thumbnail
      const thumbnail = await generateThumbnail(file);

      const thumbPresignResponse = await fetch('/api/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          albumId,
          filename: `${photoId}_thumb.jpg`,
          contentType: 'image/jpeg',
          isThumbnail: true,
        }),
      });

      if (thumbPresignResponse.ok) {
        const { uploadUrl: thumbUploadUrl } = await thumbPresignResponse.json();
        await fetch(thumbUploadUrl, {
          method: 'PUT',
          body: thumbnail,
          headers: { 'Content-Type': 'image/jpeg' },
        });
      }

      setUploads((prev) =>
        prev.map((u, i) =>
          i === index ? { ...u, status: 'complete' as const, progress: 100 } : u
        )
      );

      onUploadComplete?.(photoId);
    } catch (error) {
      setUploads((prev) =>
        prev.map((u, i) =>
          i === index
            ? { ...u, status: 'error' as const, error: (error as Error).message }
            : u
        )
      );
    }
  };

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const newUploads: UploadProgress[] = acceptedFiles.map((file) => ({
        file,
        progress: 0,
        status: 'pending' as const,
      }));

      setUploads((prev) => [...prev, ...newUploads]);
      setIsUploading(true);

      const startIndex = uploads.length;

      // Upload files sequentially to avoid overwhelming the browser
      for (let i = 0; i < acceptedFiles.length; i++) {
        await uploadFile(acceptedFiles[i], startIndex + i);
      }

      setIsUploading(false);
    },
    [albumId, uploads.length]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp', '.heic', '.heif'],
    },
    disabled: isUploading,
  });

  const completedCount = uploads.filter((u) => u.status === 'complete').length;
  const errorCount = uploads.filter((u) => u.status === 'error').length;

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
          ${isDragActive ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' : 'border-slate-300 dark:border-slate-600'}
          ${isUploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary-400 hover:bg-slate-50 dark:hover:bg-slate-800'}
        `}
      >
        <input {...getInputProps()} />
        <svg
          className="w-12 h-12 mx-auto mb-4 text-slate-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        {isDragActive ? (
          <p className="text-lg text-primary-600 dark:text-primary-400">Drop photos here...</p>
        ) : (
          <>
            <p className="text-lg text-slate-600 dark:text-slate-300">
              Drag & drop photos here, or click to select
            </p>
            <p className="text-sm text-slate-400 mt-2">
              Supports JPEG, PNG, GIF, WebP, HEIC
            </p>
          </>
        )}
      </div>

      {/* Upload progress list */}
      {uploads.length > 0 && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-slate-500">
            <span>
              {completedCount} of {uploads.length} uploaded
            </span>
            {errorCount > 0 && <span className="text-red-500">{errorCount} failed</span>}
          </div>

          <div className="max-h-64 overflow-y-auto space-y-2">
            {uploads.map((upload, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-2 bg-slate-50 dark:bg-slate-800 rounded-lg"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate text-slate-700 dark:text-slate-200">
                    {upload.file.name}
                  </p>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 mt-1">
                    <div
                      className={`h-1.5 rounded-full transition-all ${
                        upload.status === 'error'
                          ? 'bg-red-500'
                          : upload.status === 'complete'
                          ? 'bg-green-500'
                          : 'bg-primary-500'
                      }`}
                      style={{ width: `${upload.progress}%` }}
                    />
                  </div>
                </div>

                <div className="flex-shrink-0">
                  {upload.status === 'complete' && (
                    <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  {upload.status === 'error' && (
                    <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  {(upload.status === 'uploading' || upload.status === 'generating-thumbnail') && (
                    <svg
                      className="w-5 h-5 text-primary-500 animate-spin"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

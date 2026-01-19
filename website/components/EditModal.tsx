'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { PhotoItem, EditOperation, StyleType } from '@/lib/types';
import { apiClient } from '@/lib/api-client';

interface EditModalProps {
  photo: PhotoItem;
  onClose: () => void;
  onSave: (newPhoto: PhotoItem) => void;
}

type OperationInfo = {
  id: EditOperation;
  name: string;
  description: string;
  icon: React.ReactNode;
  requiresAI: boolean;
};

const OPERATIONS: OperationInfo[] = [
  {
    id: 'enhance',
    name: 'Auto-Enhance',
    description: 'Improve brightness, contrast, and colors',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    requiresAI: true,
  },
  {
    id: 'upscale',
    name: 'AI Upscale',
    description: 'Increase image resolution (2x or 4x)',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
      </svg>
    ),
    requiresAI: true,
  },
  {
    id: 'remove_bg',
    name: 'Remove Background',
    description: 'Remove or replace the background',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z" />
      </svg>
    ),
    requiresAI: true,
  },
  {
    id: 'style_transfer',
    name: 'Apply Style',
    description: 'Transform into artistic styles',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
      </svg>
    ),
    requiresAI: true,
  },
];

const STYLES: { id: StyleType; name: string }[] = [
  { id: 'watercolor', name: 'Watercolor' },
  { id: 'oil_painting', name: 'Oil Painting' },
  { id: 'sketch', name: 'Pencil Sketch' },
  { id: 'anime', name: 'Anime' },
  { id: 'pop_art', name: 'Pop Art' },
  { id: 'impressionist', name: 'Impressionist' },
];

export default function EditModal({ photo, onClose, onSave }: EditModalProps) {
  const [selectedOperation, setSelectedOperation] = useState<EditOperation>('enhance');
  const [selectedStyle, setSelectedStyle] = useState<StyleType>('watercolor');
  const [selectedScale, setSelectedScale] = useState<2 | 4>(2);
  const [isProcessing, setIsProcessing] = useState(false);
  const [preview, setPreview] = useState<PhotoItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isProcessing) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose, isProcessing]);

  const handleProcess = async () => {
    setIsProcessing(true);
    setError(null);

    try {
      let result: PhotoItem;

      switch (selectedOperation) {
        case 'enhance':
          result = await apiClient.photos.enhance(photo.id);
          break;
        case 'upscale':
          result = await apiClient.photos.upscale(photo.id, selectedScale);
          break;
        case 'remove_bg':
          result = await apiClient.photos.removeBackground(photo.id);
          break;
        case 'style_transfer':
          result = await apiClient.photos.styleTransfer(photo.id, selectedStyle);
          break;
        default:
          throw new Error('Unknown operation');
      }

      setPreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSave = () => {
    if (preview) {
      onSave(preview);
    }
  };

  const handleReset = () => {
    setPreview(null);
    setError(null);
  };

  return (
    <div
      className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isProcessing) {
          onClose();
        }
      }}
    >
      <div className="bg-gray-900 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-xl font-semibold text-white">Edit Photo with AI</h2>
          <button
            onClick={onClose}
            disabled={isProcessing}
            className="p-2 text-gray-400 hover:text-white rounded-lg transition-colors disabled:opacity-50"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* Left panel - Operations */}
          <div className="w-72 border-r border-gray-800 p-4 overflow-y-auto">
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
              Operations
            </h3>

            <div className="space-y-2">
              {OPERATIONS.map((op) => (
                <button
                  key={op.id}
                  onClick={() => {
                    setSelectedOperation(op.id);
                    handleReset();
                  }}
                  disabled={isProcessing}
                  className={`w-full p-3 rounded-lg text-left transition-colors disabled:opacity-50 ${
                    selectedOperation === op.id
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={selectedOperation === op.id ? 'text-white' : 'text-gray-400'}>
                      {op.icon}
                    </div>
                    <div>
                      <div className="font-medium">{op.name}</div>
                      <div className={`text-xs ${selectedOperation === op.id ? 'text-blue-200' : 'text-gray-500'}`}>
                        {op.description}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            {/* Operation-specific options */}
            {selectedOperation === 'upscale' && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
                  Scale Factor
                </h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSelectedScale(2)}
                    disabled={isProcessing}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors disabled:opacity-50 ${
                      selectedScale === 2
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                    }`}
                  >
                    2x
                  </button>
                  <button
                    onClick={() => setSelectedScale(4)}
                    disabled={isProcessing}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors disabled:opacity-50 ${
                      selectedScale === 4
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                    }`}
                  >
                    4x
                  </button>
                </div>
              </div>
            )}

            {selectedOperation === 'style_transfer' && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
                  Style
                </h3>
                <div className="space-y-2">
                  {STYLES.map((style) => (
                    <button
                      key={style.id}
                      onClick={() => setSelectedStyle(style.id)}
                      disabled={isProcessing}
                      className={`w-full py-2 px-4 rounded-lg text-left font-medium transition-colors disabled:opacity-50 ${
                        selectedStyle === style.id
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                      }`}
                    >
                      {style.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-6 p-3 bg-yellow-900/30 rounded-lg border border-yellow-700/50">
              <p className="text-xs text-yellow-200">
                AI operations require AWS Bedrock access and may incur charges (~$0.04-0.08 per image).
              </p>
            </div>
          </div>

          {/* Right panel - Preview */}
          <div className="flex-1 p-6 flex flex-col">
            <div className="flex-1 relative bg-gray-800 rounded-lg overflow-hidden">
              <Image
                src={preview?.url || photo.url}
                alt={photo.filename || 'Photo preview'}
                fill
                className="object-contain"
                sizes="(max-width: 768px) 100vw, 50vw"
              />

              {/* Processing overlay */}
              {isProcessing && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/70">
                  <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                    <p className="text-white text-sm">
                      Processing with AI...
                    </p>
                    <p className="text-gray-400 text-xs">
                      This may take a few seconds
                    </p>
                  </div>
                </div>
              )}

              {/* Preview badge */}
              {preview && !isProcessing && (
                <div className="absolute top-4 left-4 px-3 py-1 bg-green-600 text-white text-sm rounded-full">
                  Preview
                </div>
              )}
            </div>

            {/* Error message */}
            {error && (
              <div className="mt-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg">
                <p className="text-red-200 text-sm">{error}</p>
              </div>
            )}

            {/* Action buttons */}
            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-gray-400">
                {preview ? (
                  <span>New photo will be saved to your album</span>
                ) : (
                  <span>Original photo: {photo.filename}</span>
                )}
              </div>

              <div className="flex gap-3">
                {preview ? (
                  <>
                    <button
                      onClick={handleReset}
                      disabled={isProcessing}
                      className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors disabled:opacity-50"
                    >
                      Try Again
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={isProcessing}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 transition-colors disabled:opacity-50"
                    >
                      Save to Album
                    </button>
                  </>
                ) : (
                  <button
                    onClick={handleProcess}
                    disabled={isProcessing}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {isProcessing ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Apply {OPERATIONS.find(o => o.id === selectedOperation)?.name}
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

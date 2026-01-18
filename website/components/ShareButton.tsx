'use client';

import { useState } from 'react';

interface ShareButtonProps {
  albumId: string;
  albumName: string;
}

export default function ShareButton({ albumId, albumName }: ShareButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [expiresInDays, setExpiresInDays] = useState<number | null>(null);

  const generateShareLink = async () => {
    setIsLoading(true);
    try {
      // Generate share link locally (for demo/static export)
      const linkId = `${Date.now().toString(36)}${Math.random().toString(36).substr(2, 10)}`;

      // Store share link data in localStorage
      const storedLinks = localStorage.getItem('photo-share-links');
      const links = storedLinks ? JSON.parse(storedLinks) : {};

      const linkData: {
        albumId: string;
        albumName: string;
        createdAt: string;
        expiresAt?: string;
      } = {
        albumId,
        albumName,
        createdAt: new Date().toISOString(),
      };

      if (expiresInDays) {
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + expiresInDays);
        linkData.expiresAt = expiresAt.toISOString();
      }

      links[linkId] = linkData;
      localStorage.setItem('photo-share-links', JSON.stringify(links));

      const baseUrl = window.location.origin;
      setShareLink(`${baseUrl}/shared/?token=${linkId}`);
    } catch (error) {
      console.error('Error creating share link:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = async () => {
    if (!shareLink) return;

    try {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
          />
        </svg>
        Share Album
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="bg-white dark:bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                Share "{albumName}"
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {!shareLink ? (
              <>
                <p className="text-slate-600 dark:text-slate-300 mb-4">
                  Create a shareable link for this album. Anyone with the link can view the photos.
                </p>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                    Link expiration (optional)
                  </label>
                  <select
                    value={expiresInDays ?? ''}
                    onChange={(e) => setExpiresInDays(e.target.value ? Number(e.target.value) : null)}
                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                  >
                    <option value="">Never expires</option>
                    <option value="1">1 day</option>
                    <option value="7">7 days</option>
                    <option value="30">30 days</option>
                    <option value="90">90 days</option>
                  </select>
                </div>

                <button
                  onClick={generateShareLink}
                  disabled={isLoading}
                  className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Creating...
                    </>
                  ) : (
                    'Create Share Link'
                  )}
                </button>
              </>
            ) : (
              <>
                <p className="text-slate-600 dark:text-slate-300 mb-4">
                  Share this link with family and friends:
                </p>

                <div className="flex gap-2 mb-4">
                  <input
                    type="text"
                    value={shareLink}
                    readOnly
                    className="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                  />
                  <button
                    onClick={copyToClipboard}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                      copied
                        ? 'bg-green-500 text-white'
                        : 'bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-white hover:bg-slate-300 dark:hover:bg-slate-500'
                    }`}
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>

                <button
                  onClick={() => {
                    setShareLink(null);
                    setIsOpen(false);
                  }}
                  className="w-full py-2 px-4 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                >
                  Done
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

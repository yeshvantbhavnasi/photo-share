'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api-client';

interface MigrationPromptProps {
  onMigrationComplete: () => void;
}

export default function MigrationPrompt({ onMigrationComplete }: MigrationPromptProps) {
  const [isMigrating, setIsMigrating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ migratedCount: number } | null>(null);

  const handleMigrate = async () => {
    setIsMigrating(true);
    setError(null);

    try {
      const migrationResult = await apiClient.migrate.fromDefaultUser();
      setResult(migrationResult);

      // Wait a moment to show success, then refresh
      setTimeout(() => {
        onMigrationComplete();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Migration failed');
    } finally {
      setIsMigrating(false);
    }
  };

  if (result) {
    return (
      <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-xl p-6 mb-8">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0">
            <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-green-800 dark:text-green-200">
              Migration Complete
            </h3>
            <p className="text-green-700 dark:text-green-300">
              Successfully migrated {result.migratedCount} items to your account. Refreshing...
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-xl p-6 mb-8">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0">
          <svg className="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-blue-800 dark:text-blue-200 mb-2">
            Existing Albums Found
          </h3>
          <p className="text-blue-700 dark:text-blue-300 mb-4">
            We found albums that were created before authentication was enabled.
            Would you like to claim them and add them to your account?
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleMigrate}
              disabled={isMigrating}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              {isMigrating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                  Migrating...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  Claim Albums
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

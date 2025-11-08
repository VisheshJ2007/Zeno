/**
 * Image Preview Component
 * Displays uploaded image with preview and remove functionality
 */

import React from 'react';
import type { ImagePreviewProps } from '../types/ocr.types';
import { SimpleProgressBar } from './ProgressBar';

/**
 * ImagePreview component for displaying uploaded files
 */
export function ImagePreview({
  file,
  onRemove,
  showProgress = false,
}: ImagePreviewProps): JSX.Element {
  const { id, preview, metadata, status, progress = 0, error } = file;

  // Status badge colors
  const statusColors = {
    pending: 'bg-gray-100 text-gray-800',
    processing: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Get file icon based on type
  const getFileIcon = (fileType: string): JSX.Element => {
    if (fileType === 'application/pdf') {
      return (
        <svg
          className="w-6 h-6 text-red-500"
          fill="currentColor"
          viewBox="0 0 20 20"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            fillRule="evenodd"
            d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
            clipRule="evenodd"
          />
        </svg>
      );
    }
    return (
      <svg
        className="w-6 h-6 text-blue-500"
        fill="currentColor"
        viewBox="0 0 20 20"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          fillRule="evenodd"
          d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
          clipRule="evenodd"
        />
      </svg>
    );
  };

  return (
    <div
      className={`relative bg-white border-2 rounded-lg p-4 transition-all duration-200 ${
        status === 'error'
          ? 'border-red-300 bg-red-50'
          : status === 'completed'
          ? 'border-green-300 bg-green-50'
          : status === 'processing'
          ? 'border-blue-300 bg-blue-50'
          : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      {/* Remove button */}
      <button
        onClick={() => onRemove(id)}
        className="absolute top-2 right-2 p-1 rounded-full bg-white shadow-md hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
        aria-label="Remove file"
        disabled={status === 'processing'}
      >
        <svg
          className="w-5 h-5 text-gray-600 hover:text-red-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>

      <div className="flex items-start space-x-4">
        {/* Image preview or file icon */}
        <div className="flex-shrink-0">
          {metadata.file_type.startsWith('image/') ? (
            <img
              src={preview}
              alt={metadata.original_filename}
              className="w-20 h-20 object-cover rounded-md border border-gray-200"
            />
          ) : (
            <div className="w-20 h-20 flex items-center justify-center bg-gray-100 rounded-md border border-gray-200">
              {getFileIcon(metadata.file_type)}
            </div>
          )}
        </div>

        {/* File info */}
        <div className="flex-1 min-w-0">
          {/* Filename */}
          <p className="text-sm font-medium text-gray-900 truncate" title={metadata.original_filename}>
            {metadata.original_filename}
          </p>

          {/* File size and type */}
          <p className="text-xs text-gray-500 mt-1">
            {formatFileSize(metadata.file_size_bytes)} • {metadata.file_type.split('/')[1].toUpperCase()}
          </p>

          {/* Status badge */}
          <div className="mt-2">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[status]}`}
            >
              {status === 'pending' && 'Ready'}
              {status === 'processing' && (
                <>
                  <svg
                    className="animate-spin -ml-0.5 mr-1.5 h-3 w-3"
                    xmlns="http://www.w3.org/2000/svg"
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
                  Processing
                </>
              )}
              {status === 'completed' && (
                <>
                  <svg
                    className="-ml-0.5 mr-1.5 h-3 w-3"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Complete
                </>
              )}
              {status === 'error' && (
                <>
                  <svg
                    className="-ml-0.5 mr-1.5 h-3 w-3"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Failed
                </>
              )}
            </span>
          </div>

          {/* Progress bar */}
          {showProgress && status === 'processing' && (
            <div className="mt-3">
              <SimpleProgressBar progress={progress} />
            </div>
          )}

          {/* Error message */}
          {status === 'error' && error && (
            <p className="mt-2 text-xs text-red-600">{error}</p>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Compact image preview (grid view)
 */
export function CompactImagePreview({
  file,
  onRemove,
}: Omit<ImagePreviewProps, 'showProgress'>): JSX.Element {
  const { id, preview, metadata, status } = file;

  return (
    <div className="relative group">
      {/* Image */}
      <div
        className={`w-full aspect-square rounded-lg overflow-hidden border-2 ${
          status === 'error'
            ? 'border-red-300'
            : status === 'completed'
            ? 'border-green-300'
            : status === 'processing'
            ? 'border-blue-300 animate-pulse'
            : 'border-gray-200'
        }`}
      >
        {metadata.file_type.startsWith('image/') ? (
          <img
            src={preview}
            alt={metadata.original_filename}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-100">
            <svg
              className="w-12 h-12 text-gray-400"
              fill="currentColor"
              viewBox="0 0 20 20"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                fillRule="evenodd"
                d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        )}

        {/* Status overlay */}
        {status === 'processing' && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
            <svg
              className="animate-spin h-8 w-8 text-white"
              xmlns="http://www.w3.org/2000/svg"
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
          </div>
        )}

        {status === 'completed' && (
          <div className="absolute top-2 left-2 bg-green-500 rounded-full p-1">
            <svg
              className="h-4 w-4 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        )}
      </div>

      {/* Remove button (shows on hover) */}
      <button
        onClick={() => onRemove(id)}
        className="absolute -top-2 -right-2 p-1.5 rounded-full bg-white shadow-lg opacity-0 group-hover:opacity-100 transition-opacity focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
        aria-label="Remove file"
        disabled={status === 'processing'}
      >
        <svg
          className="w-4 h-4 text-red-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>

      {/* Filename */}
      <p className="mt-2 text-xs text-gray-600 truncate" title={metadata.original_filename}>
        {metadata.original_filename}
      </p>
    </div>
  );
}

/**
 * Example usage:
 *
 * <ImagePreview
 *   file={uploadedFile}
 *   onRemove={(id) => handleRemove(id)}
 *   showProgress={true}
 * />
 *
 * <CompactImagePreview
 *   file={uploadedFile}
 *   onRemove={(id) => handleRemove(id)}
 * />
 */

export default ImagePreview;

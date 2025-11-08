/**
 * Progress Bar Component
 * Shows OCR processing progress with status indicators
 */

import React from 'react';
import type { ProgressBarProps } from '../types/ocr.types';

/**
 * ProgressBar component for showing OCR processing progress
 */
export function ProgressBar({
  progress,
  status,
  label,
  showPercentage = true,
}: ProgressBarProps): JSX.Element {
  // Clamp progress between 0 and 100
  const clampedProgress = Math.min(100, Math.max(0, progress));

  // Status color mapping
  const statusColors = {
    processing: {
      bg: 'bg-blue-600',
      text: 'text-blue-600',
      ring: 'ring-blue-500',
    },
    complete: {
      bg: 'bg-green-600',
      text: 'text-green-600',
      ring: 'ring-green-500',
    },
    error: {
      bg: 'bg-red-600',
      text: 'text-red-600',
      ring: 'ring-red-500',
    },
  };

  const colors = statusColors[status];

  // Status icons
  const statusIcons = {
    processing: (
      <svg
        className="animate-spin h-5 w-5 text-blue-600"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
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
    ),
    complete: (
      <svg
        className="h-5 w-5 text-green-600"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
          clipRule="evenodd"
        />
      </svg>
    ),
    error: (
      <svg
        className="h-5 w-5 text-red-600"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
          clipRule="evenodd"
        />
      </svg>
    ),
  };

  return (
    <div className="w-full" role="progressbar" aria-valuenow={clampedProgress} aria-valuemin={0} aria-valuemax={100}>
      {/* Label and percentage */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          {statusIcons[status]}
          {label && (
            <span className={`text-sm font-medium ${colors.text}`}>
              {label}
            </span>
          )}
        </div>
        {showPercentage && (
          <span className={`text-sm font-semibold ${colors.text}`}>
            {clampedProgress}%
          </span>
        )}
      </div>

      {/* Progress bar container */}
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden shadow-inner">
        {/* Progress bar fill */}
        <div
          className={`h-full ${colors.bg} transition-all duration-300 ease-out rounded-full ${
            status === 'processing' ? 'animate-pulse' : ''
          }`}
          style={{ width: `${clampedProgress}%` }}
        />
      </div>

      {/* Accessibility text */}
      <span className="sr-only">
        {status === 'processing' && `Processing: ${clampedProgress}% complete`}
        {status === 'complete' && 'Processing complete'}
        {status === 'error' && 'Processing failed'}
      </span>
    </div>
  );
}

/**
 * Simplified progress bar without icons (lightweight version)
 */
export function SimpleProgressBar({
  progress,
  className = '',
}: {
  progress: number;
  className?: string;
}): JSX.Element {
  const clampedProgress = Math.min(100, Math.max(0, progress));

  return (
    <div className={`w-full bg-gray-200 rounded-full h-2 overflow-hidden ${className}`}>
      <div
        className="h-full bg-blue-600 transition-all duration-300 ease-out rounded-full"
        style={{ width: `${clampedProgress}%` }}
        role="progressbar"
        aria-valuenow={clampedProgress}
        aria-valuemin={0}
        aria-valuemax={100}
      />
    </div>
  );
}

/**
 * Circular progress indicator
 */
export function CircularProgress({
  progress,
  size = 64,
  strokeWidth = 4,
  status = 'processing',
}: {
  progress: number;
  size?: number;
  strokeWidth?: number;
  status?: 'processing' | 'complete' | 'error';
}): JSX.Element {
  const clampedProgress = Math.min(100, Math.max(0, progress));
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (clampedProgress / 100) * circumference;

  const colors = {
    processing: 'text-blue-600',
    complete: 'text-green-600',
    error: 'text-red-600',
  };

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          className="text-gray-200"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${colors[status]} transition-all duration-300`}
        />
      </svg>
      {/* Percentage text */}
      <span className={`absolute text-sm font-semibold ${colors[status]}`}>
        {Math.round(clampedProgress)}%
      </span>
    </div>
  );
}

/**
 * Example usage:
 *
 * <ProgressBar
 *   progress={75}
 *   status="processing"
 *   label="Processing image"
 *   showPercentage={true}
 * />
 *
 * <SimpleProgressBar progress={50} />
 *
 * <CircularProgress progress={80} status="processing" />
 */

export default ProgressBar;

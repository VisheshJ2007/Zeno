/**
 * OCR Uploader Component
 * Main component for uploading images, processing with OCR, and sending to backend
 */

'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import type {
  OCRUploaderProps,
  UploadedFile,
  SupportedFileType,
  ProcessingStatus,
  ToastNotification,
} from '../types/ocr.types';
import { OCRProcessor } from '../utils/ocrProcessor';
import { cleanOCRText, cleanMathematicalText, containsMathematicalNotation } from '../utils/textCleaner';
import { analyzeDocumentStructure } from '../utils/structureAnalyzer';
import { createTranscriptionRequest, submitTranscription, validateTranscriptionRequest } from '../utils/apiClient';
import { ImagePreview } from './ImagePreview';
import { ProgressBar } from './ProgressBar';

const DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const DEFAULT_ALLOWED_TYPES: SupportedFileType[] = [
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/webp',
  'application/pdf',
];

/**
 * Main OCR Uploader Component
 */
export function OCRUploader({
  onTranscriptionComplete,
  onError,
  maxFileSize = DEFAULT_MAX_FILE_SIZE,
  allowedTypes = DEFAULT_ALLOWED_TYPES,
  userId,
  maxFiles = 10,
}: OCRUploaderProps): JSX.Element {
  // State
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus>('idle');
  const [overallProgress, setOverallProgress] = useState(0);
  const [toast, setToast] = useState<ToastNotification | null>(null);

  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  const ocrProcessorRef = useRef<OCRProcessor | null>(null);

  // Initialize OCR processor
  useEffect(() => {
    ocrProcessorRef.current = new OCRProcessor();

    ocrProcessorRef.current.initialize((progress, status) => {
      console.log(`OCR initialization: ${status} (${progress}%)`);
    });

    return () => {
      // Cleanup on unmount
      ocrProcessorRef.current?.terminate();
    };
  }, []);

  // Show toast notification
  const showToast = useCallback((type: ToastNotification['type'], message: string) => {
    const id = Date.now().toString();
    setToast({ id, type, message, duration: 5000 });

    // Auto-hide after duration
    setTimeout(() => {
      setToast(null);
    }, 5000);
  }, []);

  // Validate file
  const validateFile = useCallback(
    (file: File): { valid: boolean; error?: string } => {
      // Check file type
      if (!allowedTypes.includes(file.type as SupportedFileType)) {
        return {
          valid: false,
          error: `File type ${file.type} is not supported. Allowed types: PNG, JPG, WEBP, PDF`,
        };
      }

      // Check file size
      if (file.size > maxFileSize) {
        return {
          valid: false,
          error: `File size ${(file.size / 1024 / 1024).toFixed(1)}MB exceeds maximum of ${(maxFileSize / 1024 / 1024).toFixed(1)}MB`,
        };
      }

      return { valid: true };
    },
    [allowedTypes, maxFileSize]
  );

  // Handle file selection
  const handleFiles = useCallback(
    (fileList: FileList) => {
      const newFiles: UploadedFile[] = [];

      // Check max files limit
      if (files.length + fileList.length > maxFiles) {
        showToast('error', `Maximum ${maxFiles} files allowed`);
        return;
      }

      for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i];

        // Validate file
        const validation = validateFile(file);
        if (!validation.valid) {
          showToast('error', validation.error || 'Invalid file');
          continue;
        }

        // Create file preview
        const reader = new FileReader();
        reader.onload = (e) => {
          const uploadedFile: UploadedFile = {
            id: `${Date.now()}-${i}`,
            file,
            preview: e.target?.result as string,
            metadata: {
              original_filename: file.name,
              file_size_bytes: file.size,
              file_type: file.type as SupportedFileType,
              upload_timestamp: new Date().toISOString(),
            },
            status: 'pending',
          };

          setFiles((prev) => [...prev, uploadedFile]);
        };

        reader.readAsDataURL(file);
      }
    },
    [files.length, maxFiles, validateFile, showToast]
  );

  // Handle file input change
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
    // Reset input to allow selecting the same file again
    e.target.value = '';
  };

  // Handle drag and drop
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  // Remove file
  const handleRemoveFile = useCallback((fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  }, []);

  // Process all files
  const handleTranscribe = async () => {
    if (files.length === 0) {
      showToast('warning', 'Please upload at least one file');
      return;
    }

    const processor = ocrProcessorRef.current;
    if (!processor || !processor.isReady()) {
      showToast('error', 'OCR engine not ready. Please wait and try again.');
      return;
    }

    setProcessingStatus('processing');
    setOverallProgress(0);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];

        // Update file status
        setFiles((prev) =>
          prev.map((f) => (f.id === file.id ? { ...f, status: 'processing', progress: 0 } : f))
        );

        // Step 1: OCR Processing
        setProcessingStatus('processing');
        const ocrResult = await processor.processImage(file.file, (progress) => {
          setFiles((prev) =>
            prev.map((f) => (f.id === file.id ? { ...f, progress } : f))
          );
          setOverallProgress(((i + progress / 100) / files.length) * 100);
        });

        if (!ocrResult.success) {
          throw new Error(`OCR processing failed: ${ocrResult.error.message}`);
        }

        // Step 2: Text Cleaning
        setProcessingStatus('cleaning');
        const hasMath = containsMathematicalNotation(ocrResult.data.raw_text);
        const cleanResult = hasMath
          ? cleanMathematicalText(ocrResult.data.raw_text, ocrResult.data.confidence)
          : cleanOCRText(ocrResult.data.raw_text, ocrResult.data.confidence);

        // Update OCR data with cleaned text
        ocrResult.data.cleaned_text = cleanResult.cleaned_text;

        // Step 3: Document Analysis
        setProcessingStatus('analyzing');
        const structure = analyzeDocumentStructure(cleanResult.cleaned_text);

        // Step 4: Create API request
        const request = createTranscriptionRequest(
          file.metadata.original_filename,
          file.metadata,
          ocrResult.data,
          structure,
          userId
        );

        // Validate request
        const validation = validateTranscriptionRequest(request);
        if (!validation.valid) {
          throw new Error(`Invalid request: ${validation.errors.join(', ')}`);
        }

        // Step 5: Send to backend
        setProcessingStatus('sending');
        const apiResult = await submitTranscription(request, (uploadProgress) => {
          setOverallProgress(((i + 0.8 + uploadProgress / 500) / files.length) * 100);
        });

        if (!apiResult.success) {
          throw new Error(`API request failed: ${apiResult.error.message}`);
        }

        // Update file status to completed
        setFiles((prev) =>
          prev.map((f) => (f.id === file.id ? { ...f, status: 'completed', progress: 100 } : f))
        );

        // Call success callback
        onTranscriptionComplete(apiResult.data);
      }

      // All files processed successfully
      setProcessingStatus('complete');
      setOverallProgress(100);
      showToast('success', `Successfully processed ${files.length} file(s)`);

      // Reset after a delay
      setTimeout(() => {
        setFiles([]);
        setProcessingStatus('idle');
        setOverallProgress(0);
      }, 3000);
    } catch (error) {
      console.error('[OCRUploader] Processing error:', error);
      setProcessingStatus('error');

      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      showToast('error', errorMessage);

      // Mark current file as error
      setFiles((prev) =>
        prev.map((f) => (f.status === 'processing' ? { ...f, status: 'error', error: errorMessage } : f))
      );

      if (onError) {
        onError(errorMessage);
      }
    }
  };

  // Get status label
  const getStatusLabel = (): string => {
    switch (processingStatus) {
      case 'uploading':
        return 'Uploading files...';
      case 'initializing':
        return 'Initializing OCR engine...';
      case 'processing':
        return 'Extracting text from images...';
      case 'cleaning':
        return 'Cleaning and correcting text...';
      case 'analyzing':
        return 'Analyzing document structure...';
      case 'sending':
        return 'Sending to server...';
      case 'complete':
        return 'Processing complete!';
      case 'error':
        return 'Processing failed';
      default:
        return '';
    }
  };

  const isProcessing = ['uploading', 'initializing', 'processing', 'cleaning', 'analyzing', 'sending'].includes(
    processingStatus
  );

  return (
    <div className="w-full max-w-4xl mx-auto p-6">
      {/* Toast notification */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 animate-slide-in">
          <div
            className={`rounded-lg shadow-lg p-4 max-w-md ${
              toast.type === 'success'
                ? 'bg-green-50 border-l-4 border-green-500'
                : toast.type === 'error'
                ? 'bg-red-50 border-l-4 border-red-500'
                : toast.type === 'warning'
                ? 'bg-yellow-50 border-l-4 border-yellow-500'
                : 'bg-blue-50 border-l-4 border-blue-500'
            }`}
          >
            <div className="flex items-start">
              <p className="text-sm font-medium text-gray-900">{toast.message}</p>
              <button
                onClick={() => setToast(null)}
                className="ml-4 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400 bg-white'
        }`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <p className="mt-4 text-sm text-gray-600">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="font-medium text-blue-600 hover:text-blue-500 focus:outline-none focus:underline"
          >
            Upload files
          </button>{' '}
          or drag and drop
        </p>
        <p className="mt-1 text-xs text-gray-500">
          PNG, JPG, WEBP, PDF up to {(maxFileSize / 1024 / 1024).toFixed(0)}MB
        </p>

        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple
          accept={allowedTypes.join(',')}
          onChange={handleFileInputChange}
          disabled={isProcessing}
        />
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-6 space-y-3">
          <h3 className="text-lg font-medium text-gray-900">
            Uploaded Files ({files.length})
          </h3>
          {files.map((file) => (
            <ImagePreview
              key={file.id}
              file={file}
              onRemove={handleRemoveFile}
              showProgress={file.status === 'processing'}
            />
          ))}
        </div>
      )}

      {/* Overall progress */}
      {isProcessing && (
        <div className="mt-6">
          <ProgressBar
            progress={overallProgress}
            status="processing"
            label={getStatusLabel()}
            showPercentage={true}
          />
        </div>
      )}

      {/* Transcribe button */}
      <div className="mt-6">
        <button
          onClick={handleTranscribe}
          disabled={files.length === 0 || isProcessing}
          className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
            files.length === 0 || isProcessing
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
          }`}
        >
          {isProcessing ? (
            <span className="flex items-center justify-center">
              <svg
                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
              Processing...
            </span>
          ) : (
            'Transcribe Documents'
          )}
        </button>
      </div>

      {/* Info text */}
      <p className="mt-4 text-xs text-center text-gray-500">
        Your documents will be processed using Tesseract.js OCR engine and sent securely to our servers.
      </p>
    </div>
  );
}

/**
 * Example usage:
 *
 * <OCRUploader
 *   onTranscriptionComplete={(result) => {
 *     console.log('Transcription ID:', result.transcription_id);
 *   }}
 *   onError={(error) => {
 *     console.error('Error:', error);
 *   }}
 *   userId="user123"
 *   maxFileSize={10 * 1024 * 1024}
 *   maxFiles={10}
 * />
 */

export default OCRUploader;

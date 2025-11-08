/**
 * TypeScript Type Definitions for OCR System
 * Contains all type definitions for the OCR processing pipeline
 */

// ============================================================================
// Tesseract.js Types
// ============================================================================

/**
 * Tesseract.js worker progress callback message
 */
export interface TesseractProgress {
  status: 'loading language' | 'initializing api' | 'initialized api' | 'loading model' |
          'recognizing text' | 'recognizing language' | 'loading tesseract core' | 'compiling wasm';
  progress: number; // 0-1
  workerId?: string;
  jobId?: string;
}

/**
 * Tesseract.js word recognition result
 */
export interface TesseractWord {
  text: string;
  confidence: number;
  baseline: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
    has_baseline: boolean;
  };
  bbox: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
}

/**
 * Tesseract.js line recognition result
 */
export interface TesseractLine {
  text: string;
  confidence: number;
  baseline: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
    has_baseline: boolean;
  };
  bbox: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
  words: TesseractWord[];
}

/**
 * Tesseract.js block recognition result
 */
export interface TesseractBlock {
  paragraphs: any[];
  text: string;
  confidence: number;
  baseline: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
    has_baseline: boolean;
  };
  bbox: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
  blocktype: string;
  polygon: null;
}

/**
 * Complete Tesseract.js OCR result
 */
export interface TesseractResult {
  text: string;
  confidence: number;
  blocks: TesseractBlock[];
  lines: TesseractLine[];
  words: TesseractWord[];
  hocr?: string;
  tsv?: string;
}

// ============================================================================
// File Upload Types
// ============================================================================

/**
 * Supported file types for OCR processing
 */
export type SupportedFileType = 'image/png' | 'image/jpeg' | 'image/jpg' | 'image/webp' | 'application/pdf';

/**
 * File metadata for uploaded files
 */
export interface FileMetadata {
  original_filename: string;
  file_size_bytes: number;
  file_type: SupportedFileType;
  upload_timestamp: string; // ISO 8601 format
}

/**
 * Uploaded file with preview
 */
export interface UploadedFile {
  id: string; // Unique identifier for this file
  file: File;
  preview: string; // Data URL for preview
  metadata: FileMetadata;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress?: number; // 0-100
  error?: string;
}

// ============================================================================
// OCR Processing Types
// ============================================================================

/**
 * Text cleaning result
 */
export interface CleanedTextResult {
  cleaned_text: string;
  corrections_made: number;
  warnings: string[];
}

/**
 * Document section
 */
export interface DocumentSection {
  title: string;
  content: string;
  line_start?: number;
  line_end?: number;
}

/**
 * Document type classification
 */
export type DocumentType =
  | 'lecture_notes'
  | 'syllabus'
  | 'textbook'
  | 'problem_set'
  | 'handwritten_notes'
  | 'exam'
  | 'homework'
  | 'research_paper'
  | 'unknown';

/**
 * Academic subject detection
 */
export type AcademicSubject =
  | 'mathematics'
  | 'calculus'
  | 'algebra'
  | 'geometry'
  | 'statistics'
  | 'physics'
  | 'chemistry'
  | 'biology'
  | 'computer_science'
  | 'engineering'
  | 'english'
  | 'history'
  | 'economics'
  | 'unknown';

/**
 * Structured document analysis result
 */
export interface DocumentStructure {
  document_type: DocumentType;
  sections: DocumentSection[];
  paragraphs: string[];
  detected_subject: AcademicSubject | null;
  word_count: number;
  has_formulas: boolean;
  has_tables: boolean;
  has_lists: boolean;
}

/**
 * Complete OCR data after processing
 */
export interface OCRData {
  raw_text: string;
  cleaned_text: string;
  confidence: number;
  processing_time_ms: number;
  tesseract_version?: string;
  language: string;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

/**
 * API request payload for transcription
 */
export interface TranscriptionRequest {
  filename: string;
  file_metadata: FileMetadata;
  ocr_data: OCRData;
  structured_content: DocumentStructure;
  user_id: string;
}

/**
 * API response for transcription
 */
export interface TranscriptionResponse {
  success: boolean;
  transcription_id: string;
  message?: string;
  error?: string;
  created_at: string;
}

/**
 * API error response
 */
export interface APIError {
  detail: string;
  status_code: number;
  timestamp: string;
}

// ============================================================================
// Component Props Types
// ============================================================================

/**
 * Props for OCRUploader component
 */
export interface OCRUploaderProps {
  onTranscriptionComplete: (result: TranscriptionResponse) => void;
  onError?: (error: string) => void;
  maxFileSize?: number; // In bytes, default 10MB
  allowedTypes?: SupportedFileType[];
  userId: string;
  maxFiles?: number; // Maximum number of files to upload at once
}

/**
 * Props for ImagePreview component
 */
export interface ImagePreviewProps {
  file: UploadedFile;
  onRemove: (fileId: string) => void;
  showProgress?: boolean;
}

/**
 * Props for ProgressBar component
 */
export interface ProgressBarProps {
  progress: number; // 0-100
  status: 'processing' | 'complete' | 'error';
  label?: string;
  showPercentage?: boolean;
}

// ============================================================================
// State Management Types
// ============================================================================

/**
 * OCR processing state
 */
export type ProcessingStatus =
  | 'idle'
  | 'uploading'
  | 'initializing'
  | 'processing'
  | 'cleaning'
  | 'analyzing'
  | 'sending'
  | 'complete'
  | 'error';

/**
 * Toast notification type
 */
export interface ToastNotification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
  duration?: number; // In milliseconds
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Result type for async operations
 */
export type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

/**
 * OCR configuration options
 */
export interface OCRConfig {
  language: string;
  tesseractPath?: string;
  workerPath?: string;
  langPath?: string;
  logger?: (progress: TesseractProgress) => void;
}

/**
 * Retry configuration for API calls
 */
export interface RetryConfig {
  maxAttempts: number;
  delayMs: number;
  backoffMultiplier?: number;
  timeoutMs: number;
}

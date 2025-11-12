/**
 * API Client for OCR Transcription
 * Handles communication with backend API with retry logic and error handling
 */

import type {
  TranscriptionRequest,
  TranscriptionResponse,
  APIError,
  RetryConfig,
  Result,
} from '../types/ocr.types';

// ============================================================================
// Configuration
// ============================================================================

/**
 * Default API configuration
 */
const DEFAULT_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  delayMs: 1000,
  backoffMultiplier: 2,
  timeoutMs: 30000, // 30 seconds
};

// ============================================================================
// API Client Class
// ============================================================================

/**
 * API Client for transcription operations
 */
export class TranscriptionAPIClient {
  private baseUrl: string;
  private retryConfig: RetryConfig;
  private abortController: AbortController | null = null;

  constructor(baseUrl: string = DEFAULT_API_BASE_URL, retryConfig: Partial<RetryConfig> = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.retryConfig = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };
  }

  /**
   * Submit transcription to backend API
   */
  async submitTranscription(
    request: TranscriptionRequest,
    onProgress?: (progress: number) => void
  ): Promise<Result<TranscriptionResponse>> {
    console.log('[API] Submitting transcription to backend...');

    let lastError: Error | null = null;

    // Retry loop
    for (let attempt = 1; attempt <= this.retryConfig.maxAttempts; attempt++) {
      try {
        console.log(`[API] Attempt ${attempt}/${this.retryConfig.maxAttempts}`);

        // Update progress
        if (onProgress) {
          onProgress(Math.round((attempt - 1) / this.retryConfig.maxAttempts * 50));
        }

        // Make request
        const result = await this.makeRequest(request, onProgress);

        if (result.success) {
          console.log('[API] Transcription submitted successfully');
          return result;
        }

        lastError = result.error;

        // Don't retry on client errors (4xx)
        if (this.isClientError(result.error)) {
          console.error('[API] Client error - not retrying:', result.error.message);
          return result;
        }

        // Wait before retrying (with exponential backoff)
        if (attempt < this.retryConfig.maxAttempts) {
          const delay = this.retryConfig.delayMs * Math.pow(
            this.retryConfig.backoffMultiplier || 2,
            attempt - 1
          );
          console.log(`[API] Retrying in ${delay}ms...`);
          await this.sleep(delay);
        }
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Unknown error');
        console.error(`[API] Attempt ${attempt} failed:`, lastError);

        // Wait before retrying
        if (attempt < this.retryConfig.maxAttempts) {
          const delay = this.retryConfig.delayMs * Math.pow(
            this.retryConfig.backoffMultiplier || 2,
            attempt - 1
          );
          await this.sleep(delay);
        }
      }
    }

    // All attempts failed
    console.error('[API] All retry attempts failed');
    return {
      success: false,
      error: lastError || new Error('Failed to submit transcription after multiple attempts'),
    };
  }

  /**
   * Make HTTP request to backend
   */
  private async makeRequest(
    request: TranscriptionRequest,
    onProgress?: (progress: number) => void
  ): Promise<Result<TranscriptionResponse>> {
    // Create abort controller for timeout
    this.abortController = new AbortController();
    const timeoutId = setTimeout(() => {
      this.abortController?.abort();
    }, this.retryConfig.timeoutMs);

    try {
      const url = `${this.baseUrl}/api/ocr/transcribe`;

      console.log(`[API] POST ${url}`);

      // Simulate upload progress (since fetch doesn't support upload progress natively)
      if (onProgress) {
        onProgress(50);
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: this.abortController.signal,
      });

      clearTimeout(timeoutId);

      // Update progress
      if (onProgress) {
        onProgress(75);
      }

      // Parse response
      const data = await response.json();

      if (!response.ok) {
        // Handle HTTP errors
        const apiError: APIError = {
          detail: data.detail || `HTTP ${response.status}: ${response.statusText}`,
          status_code: response.status,
          timestamp: new Date().toISOString(),
        };

        console.error('[API] Request failed:', apiError);

        return {
          success: false,
          error: new Error(apiError.detail),
        };
      }

      // Success
      if (onProgress) {
        onProgress(100);
      }

      return {
        success: true,
        data: data as TranscriptionResponse,
      };
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          console.error('[API] Request timed out');
          return {
            success: false,
            error: new Error(`Request timed out after ${this.retryConfig.timeoutMs}ms`),
          };
        }
      }

      console.error('[API] Request failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error : new Error('Request failed'),
      };
    }
  }

  /**
   * Check if error is a client error (4xx status code)
   */
  private isClientError(error: Error): boolean {
    const message = error.message;
    return /^HTTP 4\d{2}/.test(message);
  }

  /**
   * Cancel ongoing request
   */
  cancelRequest(): void {
    if (this.abortController) {
      console.log('[API] Cancelling request...');
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Sleep for specified milliseconds
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Update base URL
   */
  setBaseUrl(url: string): void {
    this.baseUrl = url.replace(/\/$/, '');
    console.log(`[API] Base URL updated to: ${this.baseUrl}`);
  }

  /**
   * Update retry configuration
   */
  setRetryConfig(config: Partial<RetryConfig>): void {
    this.retryConfig = { ...this.retryConfig, ...config };
    console.log('[API] Retry config updated:', this.retryConfig);
  }

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<Result<{ ok: boolean }>> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
      });

      if (!response.ok) {
        return {
          success: false,
          error: new Error(`Health check failed: HTTP ${response.status}`),
        };
      }

      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error : new Error('Health check failed'),
      };
    }
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Create transcription request from OCR data
 */
export function createTranscriptionRequest(
  filename: string,
  fileMetadata: TranscriptionRequest['file_metadata'],
  ocrData: TranscriptionRequest['ocr_data'],
  structuredContent: TranscriptionRequest['structured_content'],
  userId: string
): TranscriptionRequest {
  return {
    filename,
    file_metadata: fileMetadata,
    ocr_data: ocrData,
    structured_content: structuredContent,
    user_id: userId,
  };
}

/**
 * Format API error for display
 */
export function formatAPIError(error: Error): string {
  const message = error.message;

  // Timeout error
  if (message.includes('timed out')) {
    return 'Request timed out. Please check your internet connection and try again.';
  }

  // Network error
  if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
    return 'Network error. Please check your internet connection.';
  }

  // Server error
  if (/HTTP 5\d{2}/.test(message)) {
    return 'Server error. Please try again later.';
  }

  // Client error
  if (/HTTP 4\d{2}/.test(message)) {
    return `Request error: ${message}`;
  }

  // Generic error
  return `Error: ${message}`;
}

/**
 * Validate transcription request before sending
 */
export function validateTranscriptionRequest(request: TranscriptionRequest): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Validate filename
  if (!request.filename || request.filename.trim() === '') {
    errors.push('Filename is required');
  }

  // Validate user_id
  if (!request.user_id || request.user_id.trim() === '') {
    errors.push('User ID is required');
  }

  // Validate OCR data
  if (!request.ocr_data.raw_text || request.ocr_data.raw_text.trim() === '') {
    errors.push('OCR text is empty');
  }

  if (request.ocr_data.confidence < 0 || request.ocr_data.confidence > 100) {
    errors.push('Invalid confidence score');
  }

  // Validate file metadata
  if (request.file_metadata.file_size_bytes <= 0) {
    errors.push('Invalid file size');
  }

  // Validate word count
  if (request.structured_content.word_count < 0) {
    errors.push('Invalid word count');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

// ============================================================================
// Singleton Instance
// ============================================================================

/**
 * Global API client instance
 */
let globalAPIClient: TranscriptionAPIClient | null = null;

/**
 * Get or create global API client instance
 */
export function getGlobalAPIClient(): TranscriptionAPIClient {
  if (!globalAPIClient) {
    globalAPIClient = new TranscriptionAPIClient();
  }
  return globalAPIClient;
}

/**
 * Reset global API client instance
 */
export function resetGlobalAPIClient(): void {
  if (globalAPIClient) {
    globalAPIClient.cancelRequest();
    globalAPIClient = null;
  }
}

// ============================================================================
// Convenience Functions
// ============================================================================

/**
 * Submit transcription with default client
 */
export async function submitTranscription(
  request: TranscriptionRequest,
  onProgress?: (progress: number) => void
): Promise<Result<TranscriptionResponse>> {
  const client = getGlobalAPIClient();
  return client.submitTranscription(request, onProgress);
}

/**
 * Check API health with default client
 */
export async function checkAPIHealth(): Promise<Result<{ ok: boolean }>> {
  const client = getGlobalAPIClient();
  return client.healthCheck();
}

// ============================================================================
// Example Usage
// ============================================================================

/*
// Example 1: Basic usage
import { TranscriptionAPIClient, createTranscriptionRequest } from './apiClient';

const client = new TranscriptionAPIClient('http://localhost:8000');

const request = createTranscriptionRequest(
  'document.jpg',
  {
    original_filename: 'document.jpg',
    file_size_bytes: 2048576,
    file_type: 'image/jpeg',
    upload_timestamp: new Date().toISOString(),
  },
  {
    raw_text: 'Original text...',
    cleaned_text: 'Cleaned text...',
    confidence: 85.5,
    processing_time_ms: 3200,
    language: 'eng',
  },
  {
    document_type: 'lecture_notes',
    sections: [],
    paragraphs: [],
    detected_subject: 'calculus',
    word_count: 1500,
    has_formulas: true,
    has_tables: false,
    has_lists: true,
  },
  'user123'
);

const result = await client.submitTranscription(request, (progress) => {
  console.log(`Upload progress: ${progress}%`);
});

if (result.success) {
  console.log('Transcription ID:', result.data.transcription_id);
} else {
  console.error('Error:', formatAPIError(result.error));
}

// Example 2: Using global client (recommended for React)
import { getGlobalAPIClient, submitTranscription } from './apiClient';

const result = await submitTranscription(request, (progress) => {
  setUploadProgress(progress);
});

// Example 3: Health check
import { checkAPIHealth } from './apiClient';

const healthResult = await checkAPIHealth();
if (healthResult.success && healthResult.data.ok) {
  console.log('API is healthy');
}

// Example 4: Custom retry configuration
const client = new TranscriptionAPIClient('http://localhost:8000', {
  maxAttempts: 5,
  delayMs: 2000,
  timeoutMs: 60000,
});

// Example 5: Cancel request
const client = getGlobalAPIClient();
const result = client.submitTranscription(request);
// ... later
client.cancelRequest(); // Cancel ongoing request
*/

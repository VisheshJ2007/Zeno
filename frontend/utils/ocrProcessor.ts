/**
 * OCR Processor using Tesseract.js
 * Handles image-to-text conversion with progress tracking
 */

import { createWorker, Worker, PSM, OEM } from 'tesseract.js';
import type {
  TesseractResult,
  TesseractProgress,
  OCRConfig,
  OCRData,
  Result,
} from '../types/ocr.types';

// Default configuration for Tesseract.js
const DEFAULT_CONFIG: OCRConfig = {
  language: 'eng',
  logger: (progress) => {
    console.log(`[OCR] ${progress.status}: ${(progress.progress * 100).toFixed(1)}%`);
  },
};

/**
 * OCR Processor class - manages Tesseract worker lifecycle
 */
export class OCRProcessor {
  private worker: Worker | null = null;
  private isInitialized = false;
  private config: OCRConfig;
  private progressCallback?: (progress: number, status: string) => void;

  constructor(config: Partial<OCRConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Initialize the Tesseract worker
   * Must be called before processing images
   */
  async initialize(
    onProgress?: (progress: number, status: string) => void
  ): Promise<Result<void>> {
    if (this.isInitialized && this.worker) {
      return { success: true, data: undefined };
    }

    this.progressCallback = onProgress;

    try {
      console.log('[OCR] Initializing Tesseract worker...');

      // Create worker with custom logger
      this.worker = await createWorker({
        logger: (m: TesseractProgress) => {
          const progress = Math.round(m.progress * 100);
          const status = this.formatStatus(m.status);

          // Call custom progress callback
          if (this.progressCallback) {
            this.progressCallback(progress, status);
          }

          // Call config logger
          if (this.config.logger) {
            this.config.logger(m);
          }
        },
      });

      // Load language
      await this.worker.loadLanguage(this.config.language);
      await this.worker.initialize(this.config.language);

      // Set page segmentation mode and OCR engine mode for better accuracy
      await this.worker.setParameters({
        tessedit_pageseg_mode: PSM.AUTO, // Automatic page segmentation
        tessedit_ocr_engine_mode: OEM.LSTM_ONLY, // LSTM neural network (best accuracy)
      });

      this.isInitialized = true;
      console.log('[OCR] Tesseract worker initialized successfully');

      return { success: true, data: undefined };
    } catch (error) {
      console.error('[OCR] Failed to initialize Tesseract worker:', error);
      return {
        success: false,
        error: error instanceof Error ? error : new Error('Failed to initialize OCR worker'),
      };
    }
  }

  /**
   * Process a single image file and extract text
   */
  async processImage(
    file: File | string,
    onProgress?: (progress: number) => void
  ): Promise<Result<OCRData>> {
    if (!this.isInitialized || !this.worker) {
      return {
        success: false,
        error: new Error('OCR worker not initialized. Call initialize() first.'),
      };
    }

    const startTime = Date.now();

    try {
      console.log(`[OCR] Processing image: ${typeof file === 'string' ? file : file.name}`);

      // Perform OCR recognition
      const result = await this.worker.recognize(file, {
        rotateAuto: true, // Auto-rotate images
      }, {
        logger: (m: TesseractProgress) => {
          if (m.status === 'recognizing text') {
            const progress = Math.round(m.progress * 100);
            if (onProgress) {
              onProgress(progress);
            }
          }
        },
      });

      const processingTime = Date.now() - startTime;

      // Extract OCR data
      const ocrData: OCRData = {
        raw_text: result.data.text,
        cleaned_text: result.data.text, // Will be cleaned by textCleaner
        confidence: result.data.confidence,
        processing_time_ms: processingTime,
        language: this.config.language,
      };

      console.log(
        `[OCR] Processing complete in ${processingTime}ms (confidence: ${ocrData.confidence.toFixed(2)}%)`
      );

      return { success: true, data: ocrData };
    } catch (error) {
      console.error('[OCR] Processing failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error : new Error('OCR processing failed'),
      };
    }
  }

  /**
   * Process multiple images in sequence
   */
  async processMultipleImages(
    files: File[],
    onProgress?: (currentIndex: number, totalFiles: number, progress: number) => void
  ): Promise<Result<OCRData[]>> {
    if (!this.isInitialized || !this.worker) {
      return {
        success: false,
        error: new Error('OCR worker not initialized. Call initialize() first.'),
      };
    }

    const results: OCRData[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];

      console.log(`[OCR] Processing file ${i + 1}/${files.length}: ${file.name}`);

      const result = await this.processImage(file, (progress) => {
        if (onProgress) {
          onProgress(i, files.length, progress);
        }
      });

      if (!result.success) {
        return {
          success: false,
          error: result.error,
        };
      }

      results.push(result.data);
    }

    return { success: true, data: results };
  }

  /**
   * Get detailed OCR result with blocks, lines, and words
   */
  async getDetailedResult(file: File | string): Promise<Result<TesseractResult>> {
    if (!this.isInitialized || !this.worker) {
      return {
        success: false,
        error: new Error('OCR worker not initialized. Call initialize() first.'),
      };
    }

    try {
      console.log('[OCR] Getting detailed OCR result...');

      const result = await this.worker.recognize(file, {
        rotateAuto: true,
      });

      const detailedResult: TesseractResult = {
        text: result.data.text,
        confidence: result.data.confidence,
        blocks: result.data.blocks,
        lines: result.data.lines,
        words: result.data.words,
        hocr: result.data.hocr,
        tsv: result.data.tsv,
      };

      return { success: true, data: detailedResult };
    } catch (error) {
      console.error('[OCR] Failed to get detailed result:', error);
      return {
        success: false,
        error: error instanceof Error ? error : new Error('Failed to get detailed OCR result'),
      };
    }
  }

  /**
   * Process PDF file (extracts first page for now)
   * For multi-page PDF support, consider using pdf.js to extract pages first
   */
  async processPDF(file: File): Promise<Result<OCRData>> {
    console.warn('[OCR] PDF processing: Only processing first page');
    return this.processImage(file);
  }

  /**
   * Terminate the Tesseract worker
   * Important: Call this when component unmounts to prevent memory leaks
   */
  async terminate(): Promise<void> {
    if (this.worker) {
      console.log('[OCR] Terminating Tesseract worker...');
      await this.worker.terminate();
      this.worker = null;
      this.isInitialized = false;
      console.log('[OCR] Tesseract worker terminated');
    }
  }

  /**
   * Check if worker is initialized
   */
  isReady(): boolean {
    return this.isInitialized && this.worker !== null;
  }

  /**
   * Format Tesseract status messages for user display
   */
  private formatStatus(status: string): string {
    const statusMap: Record<string, string> = {
      'loading language': 'Loading language data',
      'initializing api': 'Initializing OCR engine',
      'initialized api': 'OCR engine ready',
      'loading model': 'Loading AI model',
      'recognizing text': 'Reading text from image',
      'loading tesseract core': 'Loading Tesseract core',
      'compiling wasm': 'Preparing OCR engine',
    };

    return statusMap[status] || status;
  }

  /**
   * Get current configuration
   */
  getConfig(): OCRConfig {
    return { ...this.config };
  }

  /**
   * Update configuration (requires reinitialization)
   */
  updateConfig(newConfig: Partial<OCRConfig>): void {
    this.config = { ...this.config, ...newConfig };
    console.log('[OCR] Configuration updated. Reinitialize to apply changes.');
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Validate if file is supported for OCR processing
 */
export function isSupportedFileType(file: File): boolean {
  const supportedTypes = [
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/webp',
    'application/pdf',
  ];
  return supportedTypes.includes(file.type);
}

/**
 * Validate file size
 */
export function isValidFileSize(file: File, maxSizeBytes: number = 10 * 1024 * 1024): boolean {
  return file.size <= maxSizeBytes;
}

/**
 * Convert confidence score to human-readable quality
 */
export function getConfidenceQuality(confidence: number): {
  quality: 'excellent' | 'good' | 'fair' | 'poor';
  color: string;
  message: string;
} {
  if (confidence >= 90) {
    return {
      quality: 'excellent',
      color: 'text-green-600',
      message: 'Excellent text recognition quality',
    };
  } else if (confidence >= 75) {
    return {
      quality: 'good',
      color: 'text-blue-600',
      message: 'Good text recognition quality',
    };
  } else if (confidence >= 60) {
    return {
      quality: 'fair',
      color: 'text-yellow-600',
      message: 'Fair text recognition - may contain errors',
    };
  } else {
    return {
      quality: 'poor',
      color: 'text-red-600',
      message: 'Poor text recognition - please verify carefully',
    };
  }
}

/**
 * Create a shareable OCR processor instance
 * Use this for singleton pattern across your app
 */
let globalProcessor: OCRProcessor | null = null;

export function getGlobalOCRProcessor(): OCRProcessor {
  if (!globalProcessor) {
    globalProcessor = new OCRProcessor();
  }
  return globalProcessor;
}

export function resetGlobalOCRProcessor(): void {
  if (globalProcessor) {
    globalProcessor.terminate();
    globalProcessor = null;
  }
}

// ============================================================================
// Example Usage
// ============================================================================

/*
// Example 1: Basic usage
const processor = new OCRProcessor();

await processor.initialize((progress, status) => {
  console.log(`${status}: ${progress}%`);
});

const result = await processor.processImage(file, (progress) => {
  console.log(`Processing: ${progress}%`);
});

if (result.success) {
  console.log('Extracted text:', result.data.raw_text);
  console.log('Confidence:', result.data.confidence);
}

await processor.terminate();

// Example 2: Using global processor (recommended for React)
import { useEffect } from 'react';

function MyComponent() {
  const processor = getGlobalOCRProcessor();

  useEffect(() => {
    processor.initialize();
    return () => processor.terminate();
  }, []);

  const handleFile = async (file: File) => {
    const result = await processor.processImage(file);
    if (result.success) {
      console.log(result.data);
    }
  };

  return <button onClick={() => handleFile(myFile)}>Process</button>;
}

// Example 3: Processing multiple files
const files = [file1, file2, file3];
const result = await processor.processMultipleImages(
  files,
  (currentIndex, totalFiles, progress) => {
    console.log(`File ${currentIndex + 1}/${totalFiles}: ${progress}%`);
  }
);

if (result.success) {
  result.data.forEach((ocrData, index) => {
    console.log(`File ${index + 1} confidence:`, ocrData.confidence);
  });
}
*/

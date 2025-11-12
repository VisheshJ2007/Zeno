/**
 * Text Cleaning Utilities
 * Fixes common OCR errors and improves text quality
 */

import type { CleanedTextResult } from '../types/ocr.types';

// ============================================================================
// OCR Error Patterns
// ============================================================================

/**
 * Common OCR character confusion patterns
 * Format: [incorrect, correct]
 */
const CHARACTER_REPLACEMENTS: Array<[RegExp, string]> = [
  // Common letter confusions
  [/\bl\b/g, 'I'], // Standalone lowercase L to capital I
  [/\bO\b/g, '0'], // Standalone capital O to zero (in numeric context)
  [/rn/g, 'm'], // rn confusion with m
  [/vv/g, 'w'], // double v to w
  [/\|/g, 'I'], // Pipe to capital I

  // Common punctuation errors
  [/\s+,/g, ','], // Space before comma
  [/\s+\./g, '.'], // Space before period
  [/\s+;/g, ';'], // Space before semicolon
  [/\s+:/g, ':'], // Space before colon
  [/\s+!/g, '!'], // Space before exclamation
  [/\s+\?/g, '?'], // Space before question mark

  // Quote marks
  [/``/g, '"'], // Double backtick to quote
  [/''/g, '"'], // Double apostrophe to quote

  // Hyphenation errors
  [/(\w+)-\s+(\w+)/g, '$1$2'], // Remove hyphenation at line breaks
];

/**
 * Word-level corrections for common OCR mistakes
 */
const WORD_CORRECTIONS: Record<string, string> = {
  // Common word confusions
  'teh': 'the',
  'arid': 'and',
  'rnay': 'may',
  'rnust': 'must',
  'frorn': 'from',
  'sorne': 'some',
  'tiine': 'time',
  'vvhen': 'when',
  'vvhat': 'what',
  'vvhere': 'where',
  'vvho': 'who',
  'vvhy': 'why',
  'vvith': 'with',
  'vvill': 'will',
  'tuue': 'true',
  'faise': 'false',
};

/**
 * Mathematical symbol corrections
 */
const MATH_SYMBOL_REPLACEMENTS: Array<[RegExp, string]> = [
  [/\s*x\s*/g, ' × '], // Multiply symbol (be careful with variable x)
  [/\s*\+\s*/g, ' + '], // Plus with proper spacing
  [/\s*-\s*/g, ' - '], // Minus with proper spacing
  [/\s*=\s*/g, ' = '], // Equals with proper spacing
  [/<=>/g, '⇔'], // Equivalence
  [/=>/g, '⇒'], // Implies
  [/<=/g, '≤'], // Less than or equal
  [/>=/g, '≥'], // Greater than or equal
  [/!=/g, '≠'], // Not equal
];

// ============================================================================
// Main Cleaning Functions
// ============================================================================

/**
 * Clean OCR text by fixing common errors
 */
export function cleanOCRText(rawText: string, confidence: number): CleanedTextResult {
  const warnings: string[] = [];
  let correctionsMade = 0;
  let cleanedText = rawText;

  // Store original for comparison
  const original = rawText;

  // Step 1: Normalize whitespace
  cleanedText = normalizeWhitespace(cleanedText);

  // Step 2: Fix character-level errors
  const charResult = fixCharacterErrors(cleanedText);
  cleanedText = charResult.text;
  correctionsMade += charResult.corrections;

  // Step 3: Fix word-level errors
  const wordResult = fixWordErrors(cleanedText);
  cleanedText = wordResult.text;
  correctionsMade += wordResult.corrections;

  // Step 4: Fix punctuation
  cleanedText = fixPunctuation(cleanedText);

  // Step 5: Reconstruct hyphenated words
  cleanedText = fixHyphenation(cleanedText);

  // Step 6: Fix paragraph structure
  cleanedText = fixParagraphs(cleanedText);

  // Add warnings based on confidence
  if (confidence < 60) {
    warnings.push('Low confidence OCR result - text may contain significant errors');
  } else if (confidence < 75) {
    warnings.push('Medium confidence OCR result - please review carefully');
  }

  if (correctionsMade > 50) {
    warnings.push(`Made ${correctionsMade} corrections - original text had many errors`);
  }

  // Check if text is too short
  if (cleanedText.trim().length < 10) {
    warnings.push('Very short text detected - OCR may have failed');
  }

  console.log(`[TextCleaner] Made ${correctionsMade} corrections`);
  if (warnings.length > 0) {
    console.warn(`[TextCleaner] Warnings:`, warnings);
  }

  return {
    cleaned_text: cleanedText.trim(),
    corrections_made: correctionsMade,
    warnings,
  };
}

/**
 * Clean text specifically for mathematical content
 */
export function cleanMathematicalText(rawText: string, confidence: number): CleanedTextResult {
  const result = cleanOCRText(rawText, confidence);
  let cleanedText = result.cleaned_text;

  // Apply mathematical symbol corrections
  for (const [pattern, replacement] of MATH_SYMBOL_REPLACEMENTS) {
    const before = cleanedText;
    cleanedText = cleanedText.replace(pattern, replacement);
    if (before !== cleanedText) {
      result.corrections_made++;
    }
  }

  // Fix common mathematical notation errors
  cleanedText = cleanedText
    .replace(/\^(\d+)/g, '**$1') // Exponents
    .replace(/sqrt\(([^)]+)\)/g, '√($1)') // Square root
    .replace(/\bsum\b/gi, '∑') // Summation
    .replace(/\bpi\b/gi, 'π') // Pi
    .replace(/\btheta\b/gi, 'θ') // Theta
    .replace(/\balpha\b/gi, 'α') // Alpha
    .replace(/\bbeta\b/gi, 'β') // Beta
    .replace(/\bgamma\b/gi, 'γ'); // Gamma

  return {
    cleaned_text: cleanedText.trim(),
    corrections_made: result.corrections_made,
    warnings: result.warnings,
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Normalize whitespace (remove extra spaces, fix line breaks)
 */
function normalizeWhitespace(text: string): string {
  return text
    .replace(/\r\n/g, '\n') // Normalize line endings
    .replace(/\r/g, '\n') // Mac line endings
    .replace(/\t/g, '    ') // Replace tabs with spaces
    .replace(/ +/g, ' ') // Multiple spaces to single space
    .replace(/\n{3,}/g, '\n\n'); // Max 2 consecutive line breaks
}

/**
 * Fix character-level OCR errors
 */
function fixCharacterErrors(text: string): { text: string; corrections: number } {
  let corrections = 0;
  let result = text;

  for (const [pattern, replacement] of CHARACTER_REPLACEMENTS) {
    const before = result;
    result = result.replace(pattern, replacement);

    // Count replacements
    const matches = before.match(pattern);
    if (matches) {
      corrections += matches.length;
    }
  }

  return { text: result, corrections };
}

/**
 * Fix word-level OCR errors
 */
function fixWordErrors(text: string): { text: string; corrections: number } {
  let corrections = 0;
  let words = text.split(/\b/);

  words = words.map((word) => {
    const lowerWord = word.toLowerCase();
    if (WORD_CORRECTIONS[lowerWord]) {
      corrections++;
      // Preserve original case
      if (word[0] === word[0].toUpperCase()) {
        return WORD_CORRECTIONS[lowerWord].charAt(0).toUpperCase() +
               WORD_CORRECTIONS[lowerWord].slice(1);
      }
      return WORD_CORRECTIONS[lowerWord];
    }
    return word;
  });

  return { text: words.join(''), corrections };
}

/**
 * Fix punctuation spacing and common errors
 */
function fixPunctuation(text: string): string {
  return text
    // Fix spacing around punctuation
    .replace(/\s+([,.!?;:])/g, '$1')
    .replace(/([,.!?;:])\s*/g, '$1 ')

    // Fix quotes
    .replace(/\s+"/g, ' "')
    .replace(/"\s+/g, '" ')

    // Fix parentheses
    .replace(/\(\s+/g, '(')
    .replace(/\s+\)/g, ')')

    // Fix brackets
    .replace(/\[\s+/g, '[')
    .replace(/\s+\]/g, ']')

    // Remove space before punctuation at end of sentence
    .replace(/\s+([.!?])\s*$/gm, '$1')

    // Ensure space after punctuation
    .replace(/([.!?])([A-Z])/g, '$1 $2');
}

/**
 * Fix hyphenated words that were split across lines
 */
function fixHyphenation(text: string): string {
  // Match word-\nword pattern and join them
  return text.replace(/(\w+)-\s*\n\s*(\w+)/g, '$1$2');
}

/**
 * Fix paragraph structure
 */
function fixParagraphs(text: string): string {
  // Split into lines
  const lines = text.split('\n');
  const result: string[] = [];
  let currentParagraph = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Empty line - paragraph break
    if (line === '') {
      if (currentParagraph) {
        result.push(currentParagraph);
        currentParagraph = '';
      }
      continue;
    }

    // Line starts with bullet or number - new paragraph
    if (/^[•\-*\d]+[.)]\s/.test(line)) {
      if (currentParagraph) {
        result.push(currentParagraph);
      }
      currentParagraph = line;
      continue;
    }

    // Line is very short - likely a heading
    if (line.length < 50 && !line.endsWith('.')) {
      if (currentParagraph) {
        result.push(currentParagraph);
      }
      result.push(line);
      currentParagraph = '';
      continue;
    }

    // Continue paragraph
    if (currentParagraph) {
      // Check if previous line ends with sentence-ending punctuation
      if (/[.!?]$/.test(currentParagraph)) {
        currentParagraph += ' ' + line;
      } else {
        // Join without extra space (likely continuation)
        currentParagraph += ' ' + line;
      }
    } else {
      currentParagraph = line;
    }
  }

  // Add last paragraph
  if (currentParagraph) {
    result.push(currentParagraph);
  }

  return result.join('\n\n');
}

/**
 * Remove non-printable characters
 */
export function removeNonPrintable(text: string): string {
  // Keep printable ASCII, common Unicode, and whitespace
  return text.replace(/[^\x20-\x7E\n\r\t\u00A0-\uFFFF]/g, '');
}

/**
 * Detect if text contains mathematical notation
 */
export function containsMathematicalNotation(text: string): boolean {
  const mathPatterns = [
    /\d+\s*[+\-*/×÷]\s*\d+/, // Basic arithmetic
    /[∑∫∏√π]/, // Math symbols
    /\^\d+/, // Exponents
    /\b(sin|cos|tan|log|ln|exp)\b/i, // Functions
    /[≤≥≠≈]/, // Comparison operators
    /\b(equation|formula|theorem|proof)\b/i, // Mathematical terms
  ];

  return mathPatterns.some((pattern) => pattern.test(text));
}

/**
 * Get text statistics
 */
export function getTextStatistics(text: string): {
  characterCount: number;
  wordCount: number;
  lineCount: number;
  paragraphCount: number;
  averageWordLength: number;
  sentenceCount: number;
} {
  const characterCount = text.length;
  const words = text.match(/\b\w+\b/g) || [];
  const wordCount = words.length;
  const lineCount = text.split('\n').length;
  const paragraphCount = text.split(/\n\n+/).filter(p => p.trim()).length;
  const sentences = text.match(/[.!?]+/g) || [];
  const sentenceCount = sentences.length;

  const totalWordLength = words.reduce((sum, word) => sum + word.length, 0);
  const averageWordLength = wordCount > 0 ? totalWordLength / wordCount : 0;

  return {
    characterCount,
    wordCount,
    lineCount,
    paragraphCount,
    averageWordLength: Math.round(averageWordLength * 10) / 10,
    sentenceCount,
  };
}

/**
 * Truncate text to specified length with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Extract first N words from text
 */
export function extractFirstWords(text: string, wordCount: number): string {
  const words = text.match(/\b\w+\b/g) || [];
  return words.slice(0, wordCount).join(' ') + (words.length > wordCount ? '...' : '');
}

// ============================================================================
// Example Usage
// ============================================================================

/*
// Example 1: Basic text cleaning
const rawText = "Tliis   is  sorne  OCR  text  vvith  errors .";
const confidence = 85.5;

const result = cleanOCRText(rawText, confidence);
console.log('Cleaned text:', result.cleaned_text);
console.log('Corrections made:', result.corrections_made);
console.log('Warnings:', result.warnings);

// Example 2: Mathematical text cleaning
const mathText = "f ( x ) = x ^ 2 + 2 x + l";
const mathResult = cleanMathematicalText(mathText, 90);
console.log('Cleaned math:', mathResult.cleaned_text);

// Example 3: Text statistics
const stats = getTextStatistics(result.cleaned_text);
console.log('Word count:', stats.wordCount);
console.log('Average word length:', stats.averageWordLength);

// Example 4: Check for mathematical notation
const hasMath = containsMathematicalNotation(mathText);
console.log('Contains math:', hasMath);
*/

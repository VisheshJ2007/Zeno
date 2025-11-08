/**
 * Document Structure Analyzer
 * Analyzes cleaned text to detect document type, sections, and structure
 */

import type {
  DocumentStructure,
  DocumentSection,
  DocumentType,
  AcademicSubject,
} from '../types/ocr.types';
import { containsMathematicalNotation } from './textCleaner';

// ============================================================================
// Document Type Detection
// ============================================================================

/**
 * Document type detection patterns
 */
const DOCUMENT_TYPE_PATTERNS: Record<DocumentType, RegExp[]> = {
  syllabus: [
    /\b(syllabus|course outline|course description)\b/i,
    /\b(office hours?|instructor|professor)\b/i,
    /\b(grading policy|attendance|late work)\b/i,
    /\b(required (text)?books?|materials?)\b/i,
  ],
  lecture_notes: [
    /\b(lecture|class notes?|today'?s? (topic|lecture))\b/i,
    /\b(chapter \d+|section \d+)\b/i,
    /\b(definition|theorem|lemma|corollary|proof)\b/i,
    /\b(example|note|remark|important)\b/i,
  ],
  problem_set: [
    /\b(problem set|homework|assignment|exercise)\b/i,
    /\b(problem \d+|question \d+|exercise \d+)\b/i,
    /\b(due date|submit|turn in)\b/i,
    /\b(solve|find|calculate|prove|show that)\b/i,
  ],
  exam: [
    /\b(exam|test|quiz|midterm|final)\b/i,
    /\b(time limit|points?|score)\b/i,
    /\b(question \d+.*points?)\b/i,
    /\b(multiple choice|true.?false|short answer)\b/i,
  ],
  homework: [
    /\b(homework|hw|assignment)\b/i,
    /\b(due|submit by|turn in)\b/i,
    /\b(name:?|student:?|date:?)\b/i,
  ],
  textbook: [
    /\b(chapter|section \d+\.\d+)\b/i,
    /\b(definition|theorem|proposition)\b/i,
    /\b(exercise|problem) \d+\.\d+/i,
    /\b(figure \d+|table \d+)\b/i,
  ],
  handwritten_notes: [
    // Typically harder to detect, uses absence of other patterns
    /\b(notes?|scratch|draft)\b/i,
  ],
  research_paper: [
    /\b(abstract|introduction|methodology|results|conclusion)\b/i,
    /\b(references|bibliography|citations?)\b/i,
    /\b(figure \d+|table \d+)\b/i,
  ],
  unknown: [],
};

/**
 * Academic subject detection patterns
 */
const SUBJECT_PATTERNS: Record<AcademicSubject, RegExp[]> = {
  mathematics: [
    /\b(math|mathematics|arithmetic)\b/i,
    /\b(number theory|set theory)\b/i,
  ],
  calculus: [
    /\b(calculus|derivative|integral|limit)\b/i,
    /\b(differentiat|integrat)\b/i,
    /\b(∫|∑|∂|∇)/,
  ],
  algebra: [
    /\b(algebra|polynomial|equation|variable)\b/i,
    /\b(matrix|matrices|vector)\b/i,
    /\b(linear algebra|abstract algebra)\b/i,
  ],
  geometry: [
    /\b(geometry|triangle|circle|angle)\b/i,
    /\b(euclidean|coordinate|plane)\b/i,
  ],
  statistics: [
    /\b(statistics|probability|mean|median|mode)\b/i,
    /\b(variance|standard deviation|distribution)\b/i,
    /\b(hypothesis|regression|correlation)\b/i,
  ],
  physics: [
    /\b(physics|mechanics|thermodynamics|electromagnetism)\b/i,
    /\b(force|velocity|acceleration|energy|momentum)\b/i,
    /\b(quantum|relativity|newton)\b/i,
  ],
  chemistry: [
    /\b(chemistry|chemical|reaction|molecule)\b/i,
    /\b(atom|element|compound|bond)\b/i,
    /\b(organic|inorganic|biochemistry)\b/i,
  ],
  biology: [
    /\b(biology|cell|organism|evolution)\b/i,
    /\b(genetics|dna|rna|protein)\b/i,
    /\b(ecology|anatomy|physiology)\b/i,
  ],
  computer_science: [
    /\b(computer science|programming|algorithm|data structure)\b/i,
    /\b(software|hardware|database|network)\b/i,
    /\b(code|function|variable|loop|class)\b/i,
  ],
  engineering: [
    /\b(engineering|design|system|process)\b/i,
    /\b(mechanical|electrical|civil|chemical engineering)\b/i,
  ],
  english: [
    /\b(literature|poetry|novel|essay|author)\b/i,
    /\b(shakespeare|metaphor|theme|character)\b/i,
  ],
  history: [
    /\b(history|historical|century|era|period)\b/i,
    /\b(war|revolution|empire|civilization)\b/i,
  ],
  economics: [
    /\b(economics|economy|market|trade)\b/i,
    /\b(supply|demand|inflation|gdp)\b/i,
    /\b(micro|macro|fiscal|monetary)\b/i,
  ],
  unknown: [],
};

// ============================================================================
// Main Analysis Function
// ============================================================================

/**
 * Analyze document structure and extract metadata
 */
export function analyzeDocumentStructure(cleanedText: string): DocumentStructure {
  console.log('[StructureAnalyzer] Analyzing document structure...');

  // Detect document type
  const documentType = detectDocumentType(cleanedText);
  console.log(`[StructureAnalyzer] Detected type: ${documentType}`);

  // Extract sections
  const sections = extractSections(cleanedText);
  console.log(`[StructureAnalyzer] Found ${sections.length} sections`);

  // Extract paragraphs
  const paragraphs = extractParagraphs(cleanedText);
  console.log(`[StructureAnalyzer] Found ${paragraphs.length} paragraphs`);

  // Detect subject
  const detectedSubject = detectSubject(cleanedText);
  console.log(`[StructureAnalyzer] Detected subject: ${detectedSubject || 'unknown'}`);

  // Count words
  const wordCount = countWords(cleanedText);
  console.log(`[StructureAnalyzer] Word count: ${wordCount}`);

  // Check for formulas
  const hasFormulas = containsMathematicalNotation(cleanedText);
  console.log(`[StructureAnalyzer] Has formulas: ${hasFormulas}`);

  // Check for tables
  const hasTables = detectTables(cleanedText);
  console.log(`[StructureAnalyzer] Has tables: ${hasTables}`);

  // Check for lists
  const hasLists = detectLists(cleanedText);
  console.log(`[StructureAnalyzer] Has lists: ${hasLists}`);

  return {
    document_type: documentType,
    sections,
    paragraphs,
    detected_subject: detectedSubject,
    word_count: wordCount,
    has_formulas: hasFormulas,
    has_tables: hasTables,
    has_lists: hasLists,
  };
}

// ============================================================================
// Detection Functions
// ============================================================================

/**
 * Detect document type based on content patterns
 */
export function detectDocumentType(text: string): DocumentType {
  const scores: Record<DocumentType, number> = {
    syllabus: 0,
    lecture_notes: 0,
    problem_set: 0,
    exam: 0,
    homework: 0,
    textbook: 0,
    handwritten_notes: 0,
    research_paper: 0,
    unknown: 0,
  };

  // Count pattern matches for each document type
  for (const [type, patterns] of Object.entries(DOCUMENT_TYPE_PATTERNS)) {
    for (const pattern of patterns) {
      const matches = text.match(pattern);
      if (matches) {
        scores[type as DocumentType] += matches.length;
      }
    }
  }

  // Find type with highest score
  let maxScore = 0;
  let detectedType: DocumentType = 'unknown';

  for (const [type, score] of Object.entries(scores)) {
    if (score > maxScore) {
      maxScore = score;
      detectedType = type as DocumentType;
    }
  }

  // Require minimum threshold
  if (maxScore < 2) {
    return 'unknown';
  }

  return detectedType;
}

/**
 * Detect academic subject based on content
 */
export function detectSubject(text: string): AcademicSubject | null {
  const scores: Record<AcademicSubject, number> = {
    mathematics: 0,
    calculus: 0,
    algebra: 0,
    geometry: 0,
    statistics: 0,
    physics: 0,
    chemistry: 0,
    biology: 0,
    computer_science: 0,
    engineering: 0,
    english: 0,
    history: 0,
    economics: 0,
    unknown: 0,
  };

  // Count pattern matches for each subject
  for (const [subject, patterns] of Object.entries(SUBJECT_PATTERNS)) {
    for (const pattern of patterns) {
      const matches = text.match(pattern);
      if (matches) {
        scores[subject as AcademicSubject] += matches.length;
      }
    }
  }

  // Find subject with highest score
  let maxScore = 0;
  let detectedSubject: AcademicSubject | null = null;

  for (const [subject, score] of Object.entries(scores)) {
    if (score > maxScore && subject !== 'unknown') {
      maxScore = score;
      detectedSubject = subject as AcademicSubject;
    }
  }

  // Require minimum threshold
  if (maxScore < 2) {
    return null;
  }

  return detectedSubject;
}

/**
 * Detect if text contains tables
 */
export function detectTables(text: string): boolean {
  const tablePatterns = [
    /\|\s*\w+\s*\|/g, // Markdown table syntax
    /\t\w+\t\w+/g, // Tab-separated values
    /\n\s*[\w\d]+\s+[\w\d]+\s+[\w\d]+\s*\n/g, // Space-separated columns
  ];

  return tablePatterns.some((pattern) => pattern.test(text));
}

/**
 * Detect if text contains lists
 */
export function detectLists(text: string): boolean {
  const listPatterns = [
    /^\s*[•\-*]\s+\w+/gm, // Bullet points
    /^\s*\d+[.)]\s+\w+/gm, // Numbered lists
    /^\s*[a-z][.)]\s+\w+/gm, // Lettered lists
  ];

  return listPatterns.some((pattern) => pattern.test(text));
}

// ============================================================================
// Extraction Functions
// ============================================================================

/**
 * Extract sections from text based on headings
 */
export function extractSections(text: string): DocumentSection[] {
  const sections: DocumentSection[] = [];
  const lines = text.split('\n');

  let currentSection: DocumentSection | null = null;
  let lineStart = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Check if line is a heading
    if (isHeading(line, i, lines)) {
      // Save previous section
      if (currentSection) {
        currentSection.line_end = i - 1;
        sections.push(currentSection);
      }

      // Start new section
      currentSection = {
        title: line,
        content: '',
        line_start: i,
      };
      lineStart = i + 1;
    } else if (currentSection && line) {
      // Add content to current section
      currentSection.content += (currentSection.content ? '\n' : '') + line;
    }
  }

  // Add last section
  if (currentSection) {
    currentSection.line_end = lines.length - 1;
    sections.push(currentSection);
  }

  // If no sections found, treat entire text as one section
  if (sections.length === 0) {
    sections.push({
      title: 'Document',
      content: text,
      line_start: 0,
      line_end: lines.length - 1,
    });
  }

  return sections;
}

/**
 * Check if a line is a heading
 */
function isHeading(line: string, index: number, allLines: string[]): boolean {
  // Empty line
  if (!line.trim()) {
    return false;
  }

  // Short line (likely a heading)
  if (line.length < 60 && line.length > 2) {
    // Doesn't end with period (not a sentence)
    if (!line.endsWith('.')) {
      // Next line is empty or content (paragraph separator)
      if (index + 1 < allLines.length) {
        const nextLine = allLines[index + 1].trim();
        if (!nextLine || nextLine.length > 60) {
          return true;
        }
      }

      // Check for common heading patterns
      const headingPatterns = [
        /^(chapter|section|part|appendix)\s+\d+/i,
        /^\d+\.\s+\w+/, // Numbered heading
        /^[A-Z][a-z]+(\s+[A-Z][a-z]+)*:?$/, // Title Case
        /^[A-Z\s]+$/, // ALL CAPS
      ];

      if (headingPatterns.some((pattern) => pattern.test(line))) {
        return true;
      }
    }
  }

  return false;
}

/**
 * Extract paragraphs from text
 */
export function extractParagraphs(text: string): string[] {
  // Split by double newlines (paragraph breaks)
  const paragraphs = text
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);

  return paragraphs;
}

/**
 * Count words in text
 */
export function countWords(text: string): number {
  const words = text.match(/\b\w+\b/g);
  return words ? words.length : 0;
}

/**
 * Count sentences in text
 */
export function countSentences(text: string): number {
  const sentences = text.match(/[.!?]+/g);
  return sentences ? sentences.length : 0;
}

/**
 * Extract numbered items (questions, problems, etc.)
 */
export function extractNumberedItems(text: string): DocumentSection[] {
  const items: DocumentSection[] = [];
  const lines = text.split('\n');

  let currentItem: DocumentSection | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Match numbered item pattern
    const match = line.match(/^(\d+)[.)]\s+(.+)/);

    if (match) {
      // Save previous item
      if (currentItem) {
        currentItem.line_end = i - 1;
        items.push(currentItem);
      }

      // Start new item
      const itemNumber = match[1];
      const itemText = match[2];

      currentItem = {
        title: `Item ${itemNumber}`,
        content: itemText,
        line_start: i,
      };
    } else if (currentItem && line) {
      // Continue current item
      currentItem.content += '\n' + line;
    }
  }

  // Add last item
  if (currentItem) {
    currentItem.line_end = lines.length - 1;
    items.push(currentItem);
  }

  return items;
}

/**
 * Extract bullet points
 */
export function extractBulletPoints(text: string): string[] {
  const bullets: string[] = [];
  const lines = text.split('\n');

  for (const line of lines) {
    const match = line.match(/^\s*[•\-*]\s+(.+)/);
    if (match) {
      bullets.push(match[1].trim());
    }
  }

  return bullets;
}

/**
 * Get reading difficulty estimate (Flesch-Kincaid Grade Level approximation)
 */
export function getReadingLevel(text: string): {
  level: string;
  grade: number;
  description: string;
} {
  const words = countWords(text);
  const sentences = countSentences(text);
  const syllables = estimateSyllables(text);

  if (words === 0 || sentences === 0) {
    return { level: 'unknown', grade: 0, description: 'Unable to determine' };
  }

  // Flesch-Kincaid Grade Level formula
  const grade = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59;
  const roundedGrade = Math.max(0, Math.round(grade));

  let level: string;
  let description: string;

  if (roundedGrade <= 6) {
    level = 'elementary';
    description = 'Elementary school level';
  } else if (roundedGrade <= 8) {
    level = 'middle_school';
    description = 'Middle school level';
  } else if (roundedGrade <= 12) {
    level = 'high_school';
    description = 'High school level';
  } else if (roundedGrade <= 16) {
    level = 'college';
    description = 'College level';
  } else {
    level = 'graduate';
    description = 'Graduate school level';
  }

  return { level, grade: roundedGrade, description };
}

/**
 * Estimate syllable count (simplified algorithm)
 */
function estimateSyllables(text: string): number {
  const words = text.match(/\b\w+\b/g) || [];
  let syllableCount = 0;

  for (const word of words) {
    // Count vowel groups
    const vowelGroups = word.toLowerCase().match(/[aeiouy]+/g);
    if (vowelGroups) {
      syllableCount += vowelGroups.length;
      // Subtract silent 'e' at end
      if (word.toLowerCase().endsWith('e') && vowelGroups.length > 1) {
        syllableCount--;
      }
    } else {
      // Word with no vowels counts as 1 syllable
      syllableCount++;
    }
  }

  return syllableCount;
}

// ============================================================================
// Example Usage
// ============================================================================

/*
// Example 1: Analyze document structure
const cleanedText = `
Chapter 1: Introduction to Calculus

Calculus is the mathematical study of continuous change.

Definition 1.1: A limit is the value that a function approaches as the input approaches some value.

Example: Find the limit of f(x) = x^2 as x approaches 2.

Solution: The limit is 4.
`;

const structure = analyzeDocumentStructure(cleanedText);
console.log('Document type:', structure.document_type);
console.log('Subject:', structure.detected_subject);
console.log('Sections:', structure.sections.length);
console.log('Word count:', structure.word_count);
console.log('Has formulas:', structure.has_formulas);

// Example 2: Detect document type
const syllabusText = "Course Syllabus - Introduction to Physics. Instructor: Dr. Smith. Office Hours: Mon/Wed 2-4pm";
const type = detectDocumentType(syllabusText);
console.log('Document type:', type); // 'syllabus'

// Example 3: Extract sections
const sections = extractSections(cleanedText);
sections.forEach((section, index) => {
  console.log(`Section ${index + 1}: ${section.title}`);
  console.log(`Content: ${section.content.substring(0, 50)}...`);
});

// Example 4: Reading level
const readingLevel = getReadingLevel(cleanedText);
console.log(`Reading level: ${readingLevel.description} (Grade ${readingLevel.grade})`);
*/

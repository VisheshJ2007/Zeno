/**
 * RAG Service
 * TypeScript service for interacting with RAG API endpoints
 */

// API base URL (adjust based on your environment)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================================
// Type Definitions
// ============================================================================

export interface QuizRequest {
  course_id: string;
  topic: string;
  num_questions: number;
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface FlashcardRequest {
  course_id: string;
  topic: string;
  num_cards: number;
}

export interface LessonPlanRequest {
  course_id: string;
  topic: string;
  duration_minutes: number;
  difficulty?: string;
}

export interface SemesterPlanRequest {
  course_id: string;
  student_id: string;
  start_date: string;
  end_date: string;
  exam_date: string;
  learning_goals: string[];
  study_hours_per_week: number;
}

export interface PracticeExamRequest {
  course_id: string;
  topics: string[];
  num_questions: number;
  difficulty_distribution: {
    easy: number;
    medium: number;
    hard: number;
  };
  question_types: string[];
}

export interface ChatRequest {
  course_id: string;
  message: string;
  conversation_history?: ChatMessage[];
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface DocumentUploadComplete {
  course_id: string;
  doc_type: string;
  source_file: string;
  ocr_text: string;
  metadata?: Record<string, any>;
}

export interface SourceInfo {
  source_file: string;
  doc_type: string;
  relevance_score: number;
  metadata: Record<string, any>;
  chunk_id: string;
}

export interface UsageInfo {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

// ============================================================================
// API Client Helper
// ============================================================================

class APIClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  async request<T>(
    endpoint: string,
    method: 'GET' | 'POST' | 'PATCH' | 'DELETE' = 'GET',
    data?: any
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (data && (method === 'POST' || method === 'PATCH')) {
      options.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, options);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${method} ${endpoint}`, error);
      throw error;
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, 'GET');
  }

  async post<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, 'POST', data);
  }

  async patch<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, 'PATCH', data);
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, 'DELETE');
  }
}

// ============================================================================
// RAG Service
// ============================================================================

class RAGService {
  private client: APIClient;

  constructor(baseURL: string = API_BASE_URL) {
    this.client = new APIClient(baseURL);
  }

  // ------------------------------------------------------------------------
  // Document Processing
  // ------------------------------------------------------------------------

  /**
   * Process OCR output for RAG
   * Call this after OCR extraction completes
   */
  async processDocument(request: DocumentUploadComplete): Promise<any> {
    return this.client.post('/api/rag/process-document', request);
  }

  // ------------------------------------------------------------------------
  // Content Generation
  // ------------------------------------------------------------------------

  /**
   * Generate quiz questions on a topic
   */
  async generateQuiz(request: QuizRequest): Promise<{
    quiz_id: string;
    quiz: string;
    sources: SourceInfo[];
    usage: UsageInfo;
  }> {
    return this.client.post('/api/rag/generate-quiz', request);
  }

  /**
   * Generate flashcards for active recall
   */
  async generateFlashcards(request: FlashcardRequest): Promise<{
    flashcard_id: string;
    flashcards: string;
    sources: SourceInfo[];
  }> {
    return this.client.post('/api/rag/generate-flashcards', request);
  }

  /**
   * Generate lesson plan
   */
  async generateLessonPlan(request: LessonPlanRequest): Promise<{
    lesson_plan_id: string;
    lesson_plan: string;
    sources: SourceInfo[];
  }> {
    return this.client.post('/api/rag/generate-lesson-plan', request);
  }

  /**
   * Generate semester study plan
   */
  async generateSemesterPlan(request: SemesterPlanRequest): Promise<{
    plan_id: string;
    semester_plan: string;
    num_weeks: number;
    sources: any[];
  }> {
    return this.client.post('/api/rag/generate-semester-plan', request);
  }

  /**
   * Generate practice exam
   */
  async generatePracticeExam(request: PracticeExamRequest): Promise<{
    exam_id: string;
    practice_exam: string;
    sources: any[];
  }> {
    return this.client.post('/api/rag/generate-practice-exam', request);
  }

  // ------------------------------------------------------------------------
  // Chat
  // ------------------------------------------------------------------------

  /**
   * Chat with AI tutor (with RAG and guardrails)
   */
  async chat(request: ChatRequest): Promise<{
    response: string;
    type: string;
    sources: any[];
    triggered_rails: string[];
    usage?: UsageInfo;
  }> {
    return this.client.post('/api/chat/', request);
  }

  /**
   * Simple chat without RAG
   */
  async simpleChat(request: ChatRequest): Promise<{
    response: string;
    type: string;
    usage?: UsageInfo;
  }> {
    return this.client.post('/api/chat/simple', request);
  }

  /**
   * Test guardrails with a message
   */
  async testGuardrails(message: string): Promise<any> {
    return this.client.post(`/api/chat/test-guardrails?message=${encodeURIComponent(message)}`, {});
  }

  // ------------------------------------------------------------------------
  // Health Checks
  // ------------------------------------------------------------------------

  /**
   * Check RAG system health
   */
  async checkRAGHealth(): Promise<{
    status: string;
    components: Record<string, string>;
  }> {
    return this.client.get('/api/rag/health');
  }

  /**
   * Check guardrails health
   */
  async checkGuardrailsHealth(): Promise<{
    enabled: boolean;
    status: string;
  }> {
    return this.client.get('/api/chat/guardrails/health');
  }

  // ------------------------------------------------------------------------
  // Utility Methods
  // ------------------------------------------------------------------------

  /**
   * Parse JSON response from API
   * Many API responses return JSON as a string that needs parsing
   */
  parseJSONResponse(jsonString: string): any {
    try {
      return JSON.parse(jsonString);
    } catch (error) {
      console.error('Failed to parse JSON response:', error);
      return null;
    }
  }

  /**
   * Extract quiz questions from API response
   */
  parseQuizResponse(quiz: string): any[] {
    const parsed = this.parseJSONResponse(quiz);
    return Array.isArray(parsed) ? parsed : [];
  }

  /**
   * Extract flashcards from API response
   */
  parseFlashcardsResponse(flashcards: string): any[] {
    const parsed = this.parseJSONResponse(flashcards);
    return Array.isArray(parsed) ? parsed : [];
  }

  /**
   * Extract lesson plan from API response
   */
  parseLessonPlanResponse(lessonPlan: string): any {
    return this.parseJSONResponse(lessonPlan);
  }
}

// ============================================================================
// Export singleton instance
// ============================================================================

export const ragService = new RAGService();

// ============================================================================
// React Hooks (optional - for React/Next.js integration)
// ============================================================================

/**
 * Example React hook for using RAG service
 * Uncomment if using React/Next.js
 */

/*
import { useState, useCallback } from 'react';

export function useRAGService() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const generateQuiz = useCallback(async (request: QuizRequest) => {
    setLoading(true);
    setError(null);
    try {
      const result = await ragService.generateQuiz(request);
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const chat = useCallback(async (request: ChatRequest) => {
    setLoading(true);
    setError(null);
    try {
      const result = await ragService.chat(request);
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    generateQuiz,
    chat,
    // Add other methods as needed
  };
}
*/

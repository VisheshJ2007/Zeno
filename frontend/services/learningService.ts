/**
 * Learning Management System API Service
 * Client for interacting with spaced repetition, practice sessions, and analytics
 */

import { APIClient } from '../utils/apiClient';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

export interface StudentCard {
  card_id: string;
  student_id: string;
  course_id: string;
  content_type: 'flashcard' | 'quiz_question' | 'short_answer';
  content_ref: string;
  fsrs_params: any;
  next_review: string;
  due: boolean;
  topic: string;
  skills: string[];
  difficulty_rated: 'easy' | 'medium' | 'hard';
  review_history: any[];
  total_reviews: number;
  correct_reviews: number;
  accuracy_rate: number;
  average_time_seconds: number;
  created_at: string;
  updated_at: string;
  question_content?: {
    question_text: string;
    question_type: string;
    options?: string[];
    hint?: string;
    explanation: string;
  };
}

export interface PracticeSession {
  session_id: string;
  student_id: string;
  course_id: string;
  session_type: 'daily_review' | 'topic_focused' | 'exam_prep' | 'mixed';
  interleaved: boolean;
  target_card_count: number;
  card_ids: string[];
  card_responses: any[];
  current_index: number;
  status: 'active' | 'completed' | 'abandoned';
  started_at: string;
  completed_at?: string;
  total_time_seconds: number;
  cards_completed: number;
  cards_skipped: number;
  rating_distribution: Record<string, number>;
  topic_performance: Record<string, any>;
}

export interface SessionCard {
  card_id: string;
  topic: string;
  difficulty: string;
  question: {
    question_text: string;
    question_type: string;
    options?: string[];
    hint?: string;
  };
}

export interface TopicAnalytics {
  topic: string;
  total_attempts: number;
  correct_attempts: number;
  overall_accuracy: number;
  accuracy_by_difficulty: {
    easy: number;
    medium: number;
    hard: number;
  };
  accuracy_trend: Array<{
    date: string;
    accuracy_rate: number;
    attempts: number;
    correct: number;
    predominant_difficulty: string;
    difficulty_breakdown: Record<string, number>;
  }>;
  average_time_seconds: number;
  skills: string[];
}

export interface StudentAnalytics {
  student_id: string;
  course_id: string;
  total_cards_reviewed: number;
  overall_accuracy: number;
  total_time_minutes: number;
  active_days: number;
  current_streak_days: number;
  topic_analytics: TopicAnalytics[];
  skills_mastered: number;
  skills_in_progress: number;
  skills_not_started: number;
  overall_mastery: number;
  cards_due_today: number;
  cards_due_this_week: number;
  average_reviews_per_day: number;
  accuracy_trend_7d: number[];
  accuracy_trend_30d: number[];
  recommended_topics: string[];
  recommended_skills: string[];
}

export interface Skill {
  skill_id: string;
  name: string;
  description: string;
  topic: string;
  difficulty: 'foundational' | 'intermediate' | 'advanced';
  estimated_hours: number;
  bloom_level: string;
  prerequisites: string[];
  status: 'not_started' | 'learning' | 'reviewing' | 'mastered';
  mastery_level: number;
  confidence_score: number;
  practice_attempts: number;
  accuracy_rate: number;
  time_spent_minutes: number;
  last_practiced?: string;
}

export interface SkillChecklist {
  course_id: string;
  student_id: string;
  skills: Skill[];
  overall_progress: number;
  skills_mastered: number;
  skills_in_progress: number;
  skills_not_started: number;
  total_skills: number;
}

export interface SyllabusAlignment {
  course_id: string;
  syllabus_transcription_id: string;
  student_id?: string;
  topics: Array<{
    topic: string;
    description: string;
    materials_count: number;
    coverage_score: number;
    average_relevance: number;
    document_types: string[];
    student_progress?: number;
    sample_materials: Array<{
      source_file: string;
      doc_type: string;
      relevance: number;
    }>;
  }>;
  coverage_gaps: string[];
  overall_coverage: number;
  topics_covered: number;
  total_topics: number;
  recommendations: string[];
  analyzed_at: string;
}

// ============================================================================
// Request Types
// ============================================================================

export interface EnrollCardsRequest {
  student_id: string;
  course_id: string;
  content_refs: string[];
}

export interface ReviewCardRequest {
  rating: 1 | 2 | 3 | 4;
  time_spent_seconds: number;
}

export interface CreateSessionRequest {
  student_id: string;
  course_id: string;
  session_type?: 'daily_review' | 'topic_focused' | 'exam_prep' | 'mixed';
  target_card_count?: number;
  topics?: string[];
  interleaved?: boolean;
}

export interface SubmitCardRequest {
  card_id: string;
  rating: 1 | 2 | 3 | 4;
  time_spent_seconds: number;
}

export interface GenerateQuestionsRequest {
  course_id: string;
  topics: string[];
  num_questions_per_topic?: number;
  difficulty_distribution?: {
    easy: number;
    medium: number;
    hard: number;
  };
  question_types?: string[];
}

export interface GenerateSkillsRequest {
  course_id: string;
  syllabus_text: string;
  syllabus_transcription_id?: string;
}

// ============================================================================
// Learning Service Class
// ============================================================================

class LearningService {
  private client: APIClient;

  constructor() {
    this.client = new APIClient(API_BASE_URL);
  }

  // ========== Card Management ==========

  async enrollInCards(request: EnrollCardsRequest): Promise<any> {
    return this.client.post('/api/learning/cards/enroll', request);
  }

  async reviewCard(
    cardId: string,
    studentId: string,
    review: ReviewCardRequest
  ): Promise<any> {
    return this.client.post(
      `/api/learning/cards/${cardId}/review?student_id=${studentId}`,
      review
    );
  }

  async getDueCards(
    studentId: string,
    courseId: string,
    limit: number = 20,
    topics?: string[]
  ): Promise<{ cards: StudentCard[]; count: number }> {
    const params = new URLSearchParams({
      student_id: studentId,
      course_id: courseId,
      limit: limit.toString(),
    });

    if (topics && topics.length > 0) {
      params.append('topics', topics.join(','));
    }

    return this.client.get(`/api/learning/cards/due?${params}`);
  }

  async getCardStatistics(
    studentId: string,
    courseId: string
  ): Promise<any> {
    return this.client.get(
      `/api/learning/cards/statistics?student_id=${studentId}&course_id=${courseId}`
    );
  }

  // ========== Practice Sessions ==========

  async createSession(
    request: CreateSessionRequest
  ): Promise<{
    session_id: string;
    cards: SessionCard[];
    total_cards: number;
    estimated_time_minutes: number;
  }> {
    return this.client.post('/api/learning/sessions/create', request);
  }

  async submitCardResponse(
    sessionId: string,
    studentId: string,
    response: SubmitCardRequest
  ): Promise<any> {
    return this.client.post(
      `/api/learning/sessions/${sessionId}/submit?student_id=${studentId}`,
      response
    );
  }

  async completeSession(
    sessionId: string,
    studentId: string
  ): Promise<any> {
    return this.client.post(
      `/api/learning/sessions/${sessionId}/complete?student_id=${studentId}`,
      {}
    );
  }

  async getSession(
    sessionId: string,
    studentId: string
  ): Promise<PracticeSession> {
    return this.client.get(
      `/api/learning/sessions/${sessionId}?student_id=${studentId}`
    );
  }

  async getSessionHistory(
    studentId: string,
    courseId: string,
    limit: number = 10
  ): Promise<{ sessions: PracticeSession[]; count: number }> {
    return this.client.get(
      `/api/learning/sessions/history?student_id=${studentId}&course_id=${courseId}&limit=${limit}`
    );
  }

  // ========== Question Bank ==========

  async generateQuestions(
    request: GenerateQuestionsRequest
  ): Promise<{
    success: boolean;
    generated_count: number;
    question_ids: string[];
  }> {
    return this.client.post('/api/learning/questions/generate', request);
  }

  async getQuestionsByTopic(
    courseId: string,
    topic: string,
    limit: number = 50
  ): Promise<{ questions: any[]; count: number }> {
    return this.client.get(
      `/api/learning/questions/by-topic?course_id=${courseId}&topic=${topic}&limit=${limit}`
    );
  }

  // ========== Skills ==========

  async generateSkills(
    request: GenerateSkillsRequest
  ): Promise<{
    success: boolean;
    skills_created: number;
    skill_ids: string[];
  }> {
    return this.client.post('/api/learning/skills/generate', request);
  }

  async getSkillChecklist(
    studentId: string,
    courseId: string
  ): Promise<SkillChecklist> {
    return this.client.get(
      `/api/learning/skills/checklist?student_id=${studentId}&course_id=${courseId}`
    );
  }

  async getRecommendedSkills(
    studentId: string,
    courseId: string,
    limit: number = 5
  ): Promise<{ recommendations: any[]; count: number }> {
    return this.client.get(
      `/api/learning/skills/recommended?student_id=${studentId}&course_id=${courseId}&limit=${limit}`
    );
  }

  // ========== Analytics ==========

  async getStudentAnalytics(
    studentId: string,
    courseId: string
  ): Promise<StudentAnalytics> {
    return this.client.get(
      `/api/learning/analytics/student?student_id=${studentId}&course_id=${courseId}`
    );
  }

  async getTopicAnalytics(
    studentId: string,
    courseId: string,
    days: number = 30
  ): Promise<{ topics: TopicAnalytics[]; count: number }> {
    return this.client.get(
      `/api/learning/analytics/topics?student_id=${studentId}&course_id=${courseId}&days=${days}`
    );
  }

  // ========== Syllabus Alignment ==========

  async analyzeSyllabusAlignment(
    courseId: string,
    syllabusTranscriptionId: string,
    studentId?: string
  ): Promise<SyllabusAlignment> {
    const params = new URLSearchParams({
      course_id: courseId,
      syllabus_transcription_id: syllabusTranscriptionId,
    });

    if (studentId) {
      params.append('student_id', studentId);
    }

    return this.client.post(`/api/learning/syllabus/analyze?${params}`, {});
  }

  async getSyllabusAlignment(
    courseId: string,
    studentId?: string
  ): Promise<SyllabusAlignment> {
    const params = new URLSearchParams({
      course_id: courseId,
    });

    if (studentId) {
      params.append('student_id', studentId);
    }

    return this.client.get(`/api/learning/syllabus/alignment?${params}`);
  }

  async suggestMaterialsForTopic(
    courseId: string,
    topic: string,
    description?: string
  ): Promise<{
    topic: string;
    suggestions: any[];
    count: number;
  }> {
    const params = new URLSearchParams({
      course_id: courseId,
      topic: topic,
    });

    if (description) {
      params.append('description', description);
    }

    return this.client.get(`/api/learning/syllabus/suggest-materials?${params}`);
  }

  // ========== Health Check ==========

  async healthCheck(): Promise<any> {
    return this.client.get('/api/learning/health');
  }
}

// Export singleton instance
export const learningService = new LearningService();
export default learningService;

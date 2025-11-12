"""
Pydantic Models for RAG API
Request and response models for RAG endpoints
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============================================================================
# Document Processing Models
# ============================================================================

class DocumentUploadComplete(BaseModel):
    """Model for notifying RAG system after OCR completes"""
    course_id: str = Field(..., description="Course identifier (e.g., CS101_Fall_2024)")
    doc_type: str = Field(..., description="Document type: syllabus, lecture_notes, textbook, or exam")
    source_file: str = Field(..., description="Original filename or storage path")
    ocr_text: str = Field(..., description="Extracted text from OCR")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Generation Request Models
# ============================================================================

class QuizGenerationRequest(BaseModel):
    """Request model for quiz generation"""
    course_id: str
    topic: str = Field(..., description="Topic for quiz questions")
    num_questions: int = Field(5, ge=1, le=20, description="Number of questions (1-20)")
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$", description="Difficulty level")


class FlashcardGenerationRequest(BaseModel):
    """Request model for flashcard generation"""
    course_id: str
    topic: str = Field(..., description="Topic for flashcards")
    num_cards: int = Field(10, ge=5, le=30, description="Number of flashcards (5-30)")


class LessonPlanRequest(BaseModel):
    """Request model for lesson plan generation"""
    course_id: str
    topic: str = Field(..., description="Topic for lesson plan")
    duration_minutes: int = Field(50, ge=15, le=180, description="Lesson duration in minutes")
    difficulty: str = Field("medium", description="Difficulty level")


class SemesterPlanRequest(BaseModel):
    """Request model for semester study plan generation"""
    course_id: str
    student_id: str
    start_date: str = Field(..., description="Semester start date (ISO format)")
    end_date: str = Field(..., description="Semester end date (ISO format)")
    exam_date: str = Field(..., description="Final exam date (ISO format)")
    learning_goals: List[str] = Field(..., description="Student's learning goals")
    study_hours_per_week: int = Field(10, ge=1, le=40, description="Available study hours per week")


class PracticeExamRequest(BaseModel):
    """Request model for practice exam generation"""
    course_id: str
    topics: List[str] = Field(..., description="Topics to cover in exam")
    num_questions: int = Field(20, ge=5, le=50, description="Total number of questions")
    difficulty_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"easy": 5, "medium": 10, "hard": 5},
        description="Distribution of questions by difficulty"
    )
    question_types: List[str] = Field(
        default_factory=lambda: ["multiple_choice", "short_answer", "problem_solving"],
        description="Types of questions to include"
    )


# ============================================================================
# Response Models
# ============================================================================

class SourceInfo(BaseModel):
    """Information about a source document"""
    source_file: str
    doc_type: str
    relevance_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_id: str


class UsageInfo(BaseModel):
    """Token usage information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class QuizResponse(BaseModel):
    """Response model for quiz generation"""
    quiz_id: str
    quiz: str = Field(..., description="Generated quiz content (JSON)")
    sources: List[Dict[str, Any]]
    usage: UsageInfo


class FlashcardResponse(BaseModel):
    """Response model for flashcard generation"""
    flashcard_id: str
    flashcards: str = Field(..., description="Generated flashcards (JSON)")
    sources: List[Dict[str, Any]]


class LessonPlanResponse(BaseModel):
    """Response model for lesson plan generation"""
    lesson_plan_id: str
    lesson_plan: str = Field(..., description="Generated lesson plan (JSON)")
    sources: List[Dict[str, Any]]


class SemesterPlanResponse(BaseModel):
    """Response model for semester plan generation"""
    plan_id: str
    semester_plan: str = Field(..., description="Generated semester plan (JSON)")
    num_weeks: int
    sources: List[Dict[str, Any]]


class PracticeExamResponse(BaseModel):
    """Response model for practice exam generation"""
    exam_id: str
    practice_exam: str = Field(..., description="Generated practice exam (JSON)")
    sources: List[Dict[str, Any]]


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    components: Dict[str, str]


# ============================================================================
# Chat Models
# ============================================================================

class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., pattern="^(user|assistant|system)$", description="Message role")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    course_id: str
    message: str = Field(..., description="User message")
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )


class GuardrailInfo(BaseModel):
    """Information about triggered guardrails"""
    allowed: bool
    triggered_rails: List[str] = Field(default_factory=list)
    educational_guidance: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="AI tutor response")
    type: str = Field(..., description="Response type: rag_response or guardrail_response")
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    triggered_rails: List[str] = Field(default_factory=list)


# ============================================================================
# Administrative Models
# ============================================================================

class ReprocessRequest(BaseModel):
    """Request to reprocess existing transcription"""
    transcription_id: str
    course_id: str
    doc_type: Optional[str] = Field(None, description="Document type (will be inferred if not provided)")


class BatchProcessRequest(BaseModel):
    """Request to batch process transcriptions"""
    course_id: str
    user_id: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)

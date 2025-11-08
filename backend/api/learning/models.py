"""
Pydantic models for learning management system
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4


# ============================================================================
# FSRS Models
# ============================================================================

class FSRSParameters(BaseModel):
    """FSRS algorithm parameters (per card)"""
    stability: float = Field(default=0.0, description="Memory stability in days")
    difficulty: float = Field(default=5.0, ge=1.0, le=10.0, description="Card difficulty (1-10)")
    elapsed_days: float = Field(default=0.0, description="Days since last review")
    scheduled_days: float = Field(default=0.0, description="Scheduled interval")
    reps: int = Field(default=0, description="Number of reviews")
    lapses: int = Field(default=0, description="Number of times forgotten")
    state: Literal["new", "learning", "review", "relearning"] = Field(default="new")
    last_review: Optional[datetime] = None


class FSRSReviewResult(BaseModel):
    """Result of a single review"""
    rating: Literal[1, 2, 3, 4] = Field(description="1=Again, 2=Hard, 3=Good, 4=Easy")
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    time_spent_seconds: int = Field(ge=0)


# ============================================================================
# Student Card Models
# ============================================================================

class ReviewHistory(BaseModel):
    """Single review record"""
    reviewed_at: datetime
    rating: int = Field(ge=1, le=4, description="FSRS rating: 1-4")
    time_spent_seconds: int
    fsrs_state_before: str
    fsrs_state_after: str
    interval_days: float
    stability: float
    difficulty: float


class StudentCard(BaseModel):
    """A flashcard or question enrolled for a student"""
    card_id: str = Field(default_factory=lambda: str(uuid4()))
    student_id: str
    course_id: str

    # Content reference
    content_type: Literal["flashcard", "quiz_question", "short_answer"]
    content_ref: str = Field(description="Reference to question in question_bank")

    # FSRS state
    fsrs_params: FSRSParameters = Field(default_factory=FSRSParameters)
    next_review: datetime
    due: bool = Field(default=True, description="Is this card due for review?")

    # Metadata
    topic: str
    skills: List[str] = Field(default_factory=list, description="Skill IDs this card tests")
    difficulty_rated: Literal["easy", "medium", "hard"] = "medium"

    # Performance tracking
    review_history: List[ReviewHistory] = Field(default_factory=list)
    total_reviews: int = 0
    correct_reviews: int = 0
    accuracy_rate: float = 0.0
    average_time_seconds: float = 0.0

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StudentCardCreate(BaseModel):
    """Request to enroll a student in cards"""
    student_id: str
    course_id: str
    content_refs: List[str] = Field(description="List of question IDs to enroll")


class StudentCardUpdate(BaseModel):
    """Update card after review"""
    rating: Literal[1, 2, 3, 4]
    time_spent_seconds: int


# ============================================================================
# Practice Session Models
# ============================================================================

class SessionCardResponse(BaseModel):
    """Response to a single card in session"""
    card_id: str
    presented_at: datetime = Field(default_factory=datetime.utcnow)
    rating: Optional[Literal[1, 2, 3, 4]] = None
    time_spent_seconds: Optional[int] = None
    skipped: bool = False


class PracticeSession(BaseModel):
    """A practice session"""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    student_id: str
    course_id: str

    # Configuration
    session_type: Literal["daily_review", "topic_focused", "exam_prep", "mixed"] = "daily_review"
    interleaved: bool = True
    target_card_count: int = 20

    # Session content
    card_ids: List[str] = Field(description="Cards in this session")
    card_responses: List[SessionCardResponse] = Field(default_factory=list)
    current_index: int = 0

    # Session state
    status: Literal["active", "completed", "abandoned"] = "active"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Performance metrics
    total_time_seconds: int = 0
    cards_completed: int = 0
    cards_skipped: int = 0

    # Performance by rating
    rating_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0}
    )

    # Performance by topic
    topic_performance: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="topic -> {presented, correct, avg_time}"
    )


class PracticeSessionCreate(BaseModel):
    """Request to create practice session"""
    student_id: str
    course_id: str
    session_type: Literal["daily_review", "topic_focused", "exam_prep", "mixed"] = "daily_review"
    target_card_count: int = Field(default=20, ge=1, le=100)
    topics: Optional[List[str]] = Field(default=None, description="Filter by topics (None = all)")
    interleaved: bool = Field(default=True, description="Mix topics?")


class PracticeSessionResponse(BaseModel):
    """Response from session creation"""
    session_id: str
    cards: List[Dict]  # Full card content for frontend
    total_cards: int
    estimated_time_minutes: int


class SessionCardSubmit(BaseModel):
    """Submit response to a card in session"""
    card_id: str
    rating: Literal[1, 2, 3, 4]
    time_spent_seconds: int


class SessionComplete(BaseModel):
    """Session completion summary"""
    session_id: str
    total_cards: int
    cards_completed: int
    accuracy_rate: float
    total_time_seconds: int
    rating_distribution: Dict[str, int]
    topic_performance: Dict[str, Dict]
    new_mastery_levels: Dict[str, float]  # skill_id -> mastery


# ============================================================================
# Question Bank Models
# ============================================================================

class DistractorStats(BaseModel):
    """Statistics for a distractor (wrong answer)"""
    selected_count: int = 0
    is_correct: bool = False


class Question(BaseModel):
    """A question in the question bank"""
    question_id: str = Field(default_factory=lambda: str(uuid4()))
    course_id: str

    # Content
    question_text: str
    question_type: Literal["multiple_choice", "true_false", "short_answer", "problem_solving"]
    options: Optional[List[str]] = Field(default=None, description="For multiple choice")
    correct_answer: str
    explanation: str
    hint: Optional[str] = None

    # Metadata
    topics: List[str]
    skills_tested: List[str] = Field(default_factory=list, description="Skill IDs")
    difficulty_rated: Literal["easy", "medium", "hard"] = "medium"
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"] = "understand"

    # Performance analytics (Item Response Theory)
    times_presented: int = 0
    correct_responses: int = 0
    accuracy_rate: float = 0.0
    average_time_seconds: float = 0.0
    difficulty_actual: Optional[float] = Field(
        default=None,
        description="IRT difficulty parameter (calibrated from performance)"
    )
    discrimination_index: Optional[float] = Field(
        default=None,
        description="How well this question separates strong/weak students"
    )

    # Distractor analysis (for multiple choice)
    distractor_stats: Dict[str, DistractorStats] = Field(default_factory=dict)

    # Source
    source_materials: List[str] = Field(
        default_factory=list,
        description="chunk_ids from course_materials collection"
    )
    generated_by_rag: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_calibrated: Optional[datetime] = None


class QuestionCreate(BaseModel):
    """Create new question"""
    course_id: str
    question_text: str
    question_type: Literal["multiple_choice", "true_false", "short_answer", "problem_solving"]
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str
    hint: Optional[str] = None
    topics: List[str]
    skills_tested: List[str] = []
    difficulty_rated: Literal["easy", "medium", "hard"] = "medium"
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"] = "understand"
    source_materials: List[str] = []


class QuestionBatchGenerate(BaseModel):
    """Generate batch of questions via RAG"""
    course_id: str
    topics: List[str]
    num_questions_per_topic: int = Field(default=5, ge=1, le=20)
    difficulty_distribution: Dict[str, float] = Field(
        default_factory=lambda: {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    )
    question_types: List[str] = Field(
        default_factory=lambda: ["multiple_choice"]
    )


# ============================================================================
# Skill Tracking Models
# ============================================================================

class Skill(BaseModel):
    """A learning skill/objective"""
    skill_id: str = Field(default_factory=lambda: str(uuid4()))
    course_id: str
    syllabus_ref: Optional[str] = Field(default=None, description="Transcription ID of syllabus")

    # Content
    name: str = Field(description="e.g., 'Binary Search Trees'")
    description: str
    topic: str = Field(description="High-level topic category")

    # Difficulty & Prerequisites
    difficulty: Literal["foundational", "intermediate", "advanced"] = "intermediate"
    prerequisites: List[str] = Field(default_factory=list, description="Skill IDs required before this")
    estimated_hours: float = Field(default=2.0, description="Estimated time to master")

    # Learning resources
    source_materials: List[Dict] = Field(
        default_factory=list,
        description="[{doc_type, chunk_ids}]"
    )

    # Assessment
    assessment_questions: List[str] = Field(
        default_factory=list,
        description="Question IDs that test this skill"
    )

    # Cognitive level
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"] = "apply"

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StudentSkillProgress(BaseModel):
    """Student's progress on a specific skill"""
    student_id: str
    course_id: str
    skill_id: str

    # Status
    status: Literal["not_started", "learning", "reviewing", "mastered"] = "not_started"
    mastery_level: float = Field(default=0.0, ge=0.0, le=100.0, description="0-100%")
    confidence_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Based on recent performance")

    # Evidence
    practice_attempts: int = 0
    correct_count: int = 0
    accuracy_rate: float = 0.0

    # Time tracking
    time_spent_minutes: int = 0
    last_practiced: Optional[datetime] = None
    first_practiced: Optional[datetime] = None

    # Bloom's level achieved
    cognitive_level_achieved: Optional[Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]] = None

    # Notes
    notes: Optional[str] = Field(default=None, description="Student's personal notes")

    # Timestamps
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SkillChecklist(BaseModel):
    """Checklist view of skills for a course"""
    course_id: str
    student_id: str
    skills: List[Dict] = Field(
        description="List of skills with progress"
    )
    overall_progress: float = Field(description="Overall course mastery %")
    skills_mastered: int
    skills_in_progress: int
    skills_not_started: int
    total_skills: int


class SkillGenerateRequest(BaseModel):
    """Generate skills from syllabus"""
    course_id: str
    syllabus_text: str
    syllabus_transcription_id: Optional[str] = None


# ============================================================================
# Analytics Models
# ============================================================================

class TopicAccuracyPoint(BaseModel):
    """Single data point for topic accuracy over time"""
    date: datetime
    topic: str
    accuracy_rate: float
    difficulty_level: Literal["easy", "medium", "hard"]
    attempts: int
    correct: int


class TopicAnalytics(BaseModel):
    """Analytics for a specific topic"""
    topic: str
    total_attempts: int
    correct_attempts: int
    overall_accuracy: float

    # Accuracy by difficulty
    accuracy_by_difficulty: Dict[str, float] = Field(
        default_factory=dict,
        description="{'easy': 0.9, 'medium': 0.7, 'hard': 0.5}"
    )

    # Trend over time
    accuracy_trend: List[TopicAccuracyPoint] = Field(
        default_factory=list,
        description="Time series of accuracy"
    )

    # Average response time
    average_time_seconds: float

    # Skills associated
    skills: List[str]


class StudentAnalytics(BaseModel):
    """Comprehensive student analytics"""
    student_id: str
    course_id: str

    # Overall metrics
    total_cards_reviewed: int
    overall_accuracy: float
    total_time_minutes: int
    active_days: int
    current_streak_days: int

    # Topic-level analytics
    topic_analytics: List[TopicAnalytics]

    # Skill progress
    skills_mastered: int
    skills_in_progress: int
    skills_not_started: int
    overall_mastery: float

    # Review statistics
    cards_due_today: int
    cards_due_this_week: int
    average_reviews_per_day: float

    # Performance trends
    accuracy_trend_7d: List[float] = Field(description="Last 7 days accuracy")
    accuracy_trend_30d: List[float] = Field(description="Last 30 days accuracy")

    # Recommendations
    recommended_topics: List[str] = Field(description="Topics needing attention")
    recommended_skills: List[str] = Field(description="Skills ready to learn")


class SyllabusAlignment(BaseModel):
    """Syllabus coverage analysis"""
    course_id: str
    syllabus_transcription_id: str

    # Coverage map
    topics: List[Dict] = Field(
        description="[{topic, materials_count, coverage_score, student_progress}]"
    )

    # Gaps
    coverage_gaps: List[str] = Field(description="Topics with insufficient materials")

    # Overall metrics
    overall_coverage: float = Field(description="0-100%")
    topics_covered: int
    total_topics: int

    # Recommendations
    recommendations: List[str]

    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

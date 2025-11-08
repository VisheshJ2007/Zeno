"""
Learning Management System API Routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
import logging

from ..learning.models import (
    StudentCardCreate,
    StudentCardUpdate,
    PracticeSessionCreate,
    SessionCardSubmit,
    QuestionCreate,
    QuestionBatchGenerate,
    SkillGenerateRequest
)
from ..learning.card_manager import CardManager
from ..learning.session_manager import SessionManager
from ..learning.question_bank import QuestionBankManager
from ..learning.skill_manager import SkillManager
from ..learning.analytics import AnalyticsManager
from ..learning.syllabus_alignment import SyllabusAlignmentManager
from ...database.mongodb import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learning", tags=["Learning"])


# Dependency to get managers
def get_card_manager():
    db = get_database()
    return CardManager(db)


def get_session_manager():
    db = get_database()
    return SessionManager(db)


def get_question_manager():
    db = get_database()
    return QuestionBankManager(db)


def get_skill_manager():
    db = get_database()
    return SkillManager(db)


def get_analytics_manager():
    db = get_database()
    return AnalyticsManager(db)


def get_syllabus_manager():
    db = get_database()
    return SyllabusAlignmentManager(db)


# ============================================================================
# Card Management Endpoints
# ============================================================================

@router.post(
    "/cards/enroll",
    summary="Enroll student in cards",
    description="Enroll a student in flashcards/questions for spaced repetition"
)
async def enroll_in_cards(
    request: StudentCardCreate,
    card_manager: CardManager = Depends(get_card_manager)
):
    """Enroll student in cards for spaced repetition"""
    try:
        card_ids = await card_manager.enroll_student_in_cards(
            student_id=request.student_id,
            course_id=request.course_id,
            question_ids=request.content_refs
        )

        return {
            "success": True,
            "enrolled_count": len(card_ids),
            "card_ids": card_ids
        }

    except Exception as e:
        logger.error(f"Failed to enroll student in cards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/cards/{card_id}/review",
    summary="Submit card review",
    description="Submit a review for a card with FSRS scheduling"
)
async def review_card(
    card_id: str,
    student_id: str,
    review: StudentCardUpdate,
    card_manager: CardManager = Depends(get_card_manager)
):
    """Process card review with FSRS"""
    try:
        updated_card, next_review_info = await card_manager.review_card(
            card_id=card_id,
            student_id=student_id,
            rating=review.rating,
            time_spent_seconds=review.time_spent_seconds
        )

        return {
            "success": True,
            "card_id": card_id,
            "next_review": next_review_info,
            "accuracy_rate": updated_card["accuracy_rate"]
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to review card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/cards/due",
    summary="Get due cards",
    description="Get cards due for review"
)
async def get_due_cards(
    student_id: str,
    course_id: str,
    limit: int = 20,
    topics: Optional[str] = None,
    card_manager: CardManager = Depends(get_card_manager)
):
    """Get cards due for review"""
    try:
        topic_list = topics.split(",") if topics else None

        cards = await card_manager.get_due_cards(
            student_id=student_id,
            course_id=course_id,
            limit=limit,
            topics=topic_list
        )

        return {
            "cards": cards,
            "count": len(cards)
        }

    except Exception as e:
        logger.error(f"Failed to get due cards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/cards/statistics",
    summary="Get card statistics",
    description="Get overall card statistics for student"
)
async def get_card_statistics(
    student_id: str,
    course_id: str,
    card_manager: CardManager = Depends(get_card_manager)
):
    """Get card statistics"""
    try:
        stats = await card_manager.get_card_statistics(student_id, course_id)
        return stats

    except Exception as e:
        logger.error(f"Failed to get card statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# Practice Session Endpoints
# ============================================================================

@router.post(
    "/sessions/create",
    summary="Create practice session",
    description="Create a new practice session with interleaved cards"
)
async def create_session(
    request: PracticeSessionCreate,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Create practice session"""
    try:
        session = await session_manager.create_session(
            student_id=request.student_id,
            course_id=request.course_id,
            session_type=request.session_type,
            target_count=request.target_card_count,
            topics=request.topics,
            interleaved=request.interleaved
        )

        if "error" in session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=session["error"]
            )

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/sessions/{session_id}/submit",
    summary="Submit card response",
    description="Submit a response to a card in the session"
)
async def submit_card_response(
    session_id: str,
    student_id: str,
    response: SessionCardSubmit,
    session_manager: SessionManager = Depends(get_session_manager),
    card_manager: CardManager = Depends(get_card_manager),
    skill_manager: SkillManager = Depends(get_skill_manager),
    question_manager: QuestionBankManager = Depends(get_question_manager)
):
    """Submit response to card in session"""
    try:
        # Submit to session
        session_update = await session_manager.submit_card_response(
            session_id=session_id,
            student_id=student_id,
            card_id=response.card_id,
            rating=response.rating,
            time_spent_seconds=response.time_spent_seconds
        )

        # Update card with FSRS
        await card_manager.review_card(
            card_id=response.card_id,
            student_id=student_id,
            rating=response.rating,
            time_spent_seconds=response.time_spent_seconds
        )

        # Update question performance
        card = await card_manager.cards_collection.find_one({"_id": response.card_id})
        if card:
            question_id = card["content_ref"]
            is_correct = response.rating >= 3

            await question_manager.update_question_performance(
                question_id=question_id,
                is_correct=is_correct,
                time_spent_seconds=response.time_spent_seconds
            )

            # Update skill progress
            for skill_id in card.get("skills", []):
                await skill_manager.update_skill_progress(
                    student_id=student_id,
                    course_id=card["course_id"],
                    skill_id=skill_id,
                    is_correct=is_correct,
                    time_spent_minutes=response.time_spent_seconds // 60
                )

        return session_update

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit card response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/sessions/{session_id}/complete",
    summary="Complete session",
    description="Mark session as complete and get summary"
)
async def complete_session(
    session_id: str,
    student_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Complete practice session"""
    try:
        summary = await session_manager.complete_session(session_id, student_id)
        return summary

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to complete session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/sessions/{session_id}",
    summary="Get session details",
    description="Get details of a practice session"
)
async def get_session(
    session_id: str,
    student_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get session details"""
    try:
        session = await session_manager.get_session(session_id, student_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/sessions/history",
    summary="Get session history",
    description="Get recent practice sessions"
)
async def get_session_history(
    student_id: str,
    course_id: str,
    limit: int = 10,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get session history"""
    try:
        sessions = await session_manager.get_recent_sessions(
            student_id, course_id, limit
        )

        return {"sessions": sessions, "count": len(sessions)}

    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# Question Bank Endpoints
# ============================================================================

@router.post(
    "/questions/create",
    summary="Create question",
    description="Create a new question in the question bank"
)
async def create_question(
    request: QuestionCreate,
    question_manager: QuestionBankManager = Depends(get_question_manager)
):
    """Create new question"""
    try:
        question_id = await question_manager.create_question(
            course_id=request.course_id,
            question_text=request.question_text,
            question_type=request.question_type,
            correct_answer=request.correct_answer,
            explanation=request.explanation,
            topics=request.topics,
            options=request.options,
            hint=request.hint,
            skills_tested=request.skills_tested,
            difficulty_rated=request.difficulty_rated,
            bloom_level=request.bloom_level,
            source_materials=request.source_materials
        )

        return {
            "success": True,
            "question_id": question_id
        }

    except Exception as e:
        logger.error(f"Failed to create question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/questions/generate",
    summary="Generate questions with RAG",
    description="Generate questions using RAG from course materials"
)
async def generate_questions(
    request: QuestionBatchGenerate,
    question_manager: QuestionBankManager = Depends(get_question_manager)
):
    """Generate questions via RAG"""
    try:
        question_ids = await question_manager.generate_questions_with_rag(
            course_id=request.course_id,
            topics=request.topics,
            num_questions_per_topic=request.num_questions_per_topic,
            difficulty_distribution=request.difficulty_distribution,
            question_types=request.question_types
        )

        return {
            "success": True,
            "generated_count": len(question_ids),
            "question_ids": question_ids
        }

    except Exception as e:
        logger.error(f"Failed to generate questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/questions/by-topic",
    summary="Get questions by topic",
    description="Get questions for a specific topic"
)
async def get_questions_by_topic(
    course_id: str,
    topic: str,
    limit: int = 50,
    question_manager: QuestionBankManager = Depends(get_question_manager)
):
    """Get questions by topic"""
    try:
        questions = await question_manager.get_questions_by_topic(
            course_id, topic, limit
        )

        return {"questions": questions, "count": len(questions)}

    except Exception as e:
        logger.error(f"Failed to get questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# Skill Management Endpoints
# ============================================================================

@router.post(
    "/skills/generate",
    summary="Generate skills from syllabus",
    description="Use RAG to extract skills from syllabus"
)
async def generate_skills(
    request: SkillGenerateRequest,
    skill_manager: SkillManager = Depends(get_skill_manager)
):
    """Generate skills from syllabus"""
    try:
        skill_ids = await skill_manager.generate_skills_from_syllabus(
            course_id=request.course_id,
            syllabus_text=request.syllabus_text,
            syllabus_transcription_id=request.syllabus_transcription_id
        )

        return {
            "success": True,
            "skills_created": len(skill_ids),
            "skill_ids": skill_ids
        }

    except Exception as e:
        logger.error(f"Failed to generate skills: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/skills/checklist",
    summary="Get skill checklist",
    description="Get skill checklist with student progress"
)
async def get_skill_checklist(
    student_id: str,
    course_id: str,
    skill_manager: SkillManager = Depends(get_skill_manager)
):
    """Get skill checklist"""
    try:
        checklist = await skill_manager.get_student_checklist(student_id, course_id)
        return checklist

    except Exception as e:
        logger.error(f"Failed to get skill checklist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/skills/recommended",
    summary="Get recommended skills",
    description="Get recommended skills to work on next"
)
async def get_recommended_skills(
    student_id: str,
    course_id: str,
    limit: int = 5,
    skill_manager: SkillManager = Depends(get_skill_manager)
):
    """Get recommended skills"""
    try:
        recommendations = await skill_manager.get_recommended_skills(
            student_id, course_id, limit
        )

        return {"recommendations": recommendations, "count": len(recommendations)}

    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get(
    "/analytics/student",
    summary="Get student analytics",
    description="Get comprehensive student analytics dashboard"
)
async def get_student_analytics(
    student_id: str,
    course_id: str,
    analytics_manager: AnalyticsManager = Depends(get_analytics_manager)
):
    """Get student analytics"""
    try:
        analytics = await analytics_manager.get_student_analytics(student_id, course_id)
        return analytics

    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/analytics/topics",
    summary="Get topic analytics",
    description="Get accuracy trends by topic over time"
)
async def get_topic_analytics(
    student_id: str,
    course_id: str,
    days: int = 30,
    analytics_manager: AnalyticsManager = Depends(get_analytics_manager)
):
    """Get topic analytics"""
    try:
        analytics = await analytics_manager.get_topic_analytics(
            student_id, course_id, days
        )

        return {"topics": analytics, "count": len(analytics)}

    except Exception as e:
        logger.error(f"Failed to get topic analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# Syllabus Alignment Endpoints
# ============================================================================

@router.post(
    "/syllabus/analyze",
    summary="Analyze syllabus alignment",
    description="Analyze how well course materials cover syllabus topics"
)
async def analyze_syllabus_alignment(
    course_id: str,
    syllabus_transcription_id: str,
    student_id: Optional[str] = None,
    syllabus_manager: SyllabusAlignmentManager = Depends(get_syllabus_manager)
):
    """Analyze syllabus alignment"""
    try:
        alignment = await syllabus_manager.analyze_syllabus_coverage(
            course_id=course_id,
            syllabus_transcription_id=syllabus_transcription_id,
            student_id=student_id
        )

        return alignment

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to analyze syllabus alignment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/syllabus/alignment",
    summary="Get latest alignment report",
    description="Get the most recent syllabus alignment report"
)
async def get_syllabus_alignment(
    course_id: str,
    student_id: Optional[str] = None,
    syllabus_manager: SyllabusAlignmentManager = Depends(get_syllabus_manager)
):
    """Get syllabus alignment report"""
    try:
        alignment = await syllabus_manager.get_latest_alignment(
            course_id, student_id
        )

        if not alignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No alignment report found"
            )

        return alignment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alignment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/syllabus/suggest-materials",
    summary="Suggest materials for topic",
    description="Get RAG-suggested materials for a specific topic"
)
async def suggest_materials_for_topic(
    course_id: str,
    topic: str,
    description: Optional[str] = None,
    syllabus_manager: SyllabusAlignmentManager = Depends(get_syllabus_manager)
):
    """Suggest materials for topic"""
    try:
        suggestions = await syllabus_manager.suggest_materials_for_topic(
            course_id, topic, description
        )

        return {"topic": topic, "suggestions": suggestions, "count": len(suggestions)}

    except Exception as e:
        logger.error(f"Failed to suggest materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# Health Check
# ============================================================================

@router.get(
    "/health",
    summary="Learning system health check",
    description="Check if learning system is operational"
)
async def health_check():
    """Health check for learning system"""
    return {
        "status": "healthy",
        "service": "learning_management_system",
        "features": [
            "spaced_repetition (FSRS)",
            "practice_sessions",
            "question_bank",
            "skill_tracking",
            "analytics",
            "syllabus_alignment"
        ]
    }

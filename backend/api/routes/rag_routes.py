"""
RAG API Routes
FastAPI routes for RAG functionality: content generation, document processing, etc.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from typing import List, Dict
from datetime import datetime
import logging
import json

from ..rag.models import (
    DocumentUploadComplete,
    QuizGenerationRequest,
    FlashcardGenerationRequest,
    LessonPlanRequest,
    SemesterPlanRequest,
    PracticeExamRequest,
    ReprocessRequest,
    BatchProcessRequest
)
from ..rag.rag_engine import rag_engine
from ..rag.ocr_integration import (
    process_ocr_output_for_rag,
    reprocess_document,
    batch_process_transcriptions
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["RAG"])


# ============================================================================
# Document Processing Endpoints
# ============================================================================

@router.post(
    "/process-document",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process OCR output for RAG",
    description="Process OCR-extracted text and prepare for RAG retrieval"
)
async def process_uploaded_document(
    request: DocumentUploadComplete,
    background_tasks: BackgroundTasks
):
    """
    Process OCR output and prepare for RAG
    Called automatically after OCR completes
    """
    try:
        await process_ocr_output_for_rag(
            ocr_text=request.ocr_text,
            course_id=request.course_id,
            doc_type=request.doc_type,
            source_file=request.source_file,
            metadata=request.metadata,
            background_tasks=background_tasks
        )

        return {
            "status": "processing",
            "message": f"Document {request.source_file} is being processed for RAG",
            "course_id": request.course_id,
            "doc_type": request.doc_type
        }
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


# ============================================================================
# Content Generation Endpoints
# ============================================================================

@router.post(
    "/generate-quiz",
    summary="Generate quiz questions",
    description="Generate quiz questions on a specific topic using RAG"
)
async def generate_quiz(request: QuizGenerationRequest):
    """Generate quiz questions on a specific topic"""

    try:
        system_prompt = """You are an expert educator creating quiz questions.

Generate quiz questions that:
- Test conceptual understanding, not just memorization
- Are clear and unambiguous
- Have one definitively correct answer
- Include plausible distractors for multiple choice

Return as JSON array:
[
    {
        "question": "Question text",
        "type": "multiple_choice",
        "options": ["A", "B", "C", "D"],
        "correct_answer": "B",
        "explanation": "Why this is correct...",
        "difficulty": "medium",
        "topic": "specific topic"
    }
]
"""

        query = f"""Generate {request.num_questions} {request.difficulty} quiz questions about {request.topic}.

Include:
- Multiple choice questions with 4 options
- Clear, specific questions
- Correct answers with explanations
- Difficulty level: {request.difficulty}

Format as JSON array."""

        result = await rag_engine.generate_with_rag(
            query=query,
            course_id=request.course_id,
            system_prompt=system_prompt,
            k=5,
            filters={"metadata.topic": request.topic} if request.topic != "general" else None,
            temperature=0.3
        )

        # Store generated quiz
        quiz_doc = {
            "course_id": request.course_id,
            "content_type": "quiz",
            "prompt_used": query,
            "generated_content": result["response"],
            "source_chunks": [s["chunk_id"] for s in result["sources"]],
            "created_at": datetime.utcnow()
        }
        quiz_id = rag_engine.generated_content.insert_one(quiz_doc).inserted_id

        return {
            "quiz_id": str(quiz_id),
            "quiz": result["response"],
            "sources": result["sources"],
            "usage": result["usage"]
        }

    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quiz: {str(e)}"
        )


@router.post(
    "/generate-flashcards",
    summary="Generate flashcards",
    description="Generate flashcards for active recall practice"
)
async def generate_flashcards(request: FlashcardGenerationRequest):
    """Generate flashcards for active recall"""

    try:
        system_prompt = """You are creating flashcards for active recall practice.

Generate flashcards that:
- Have a clear question on the front
- Have a concise answer on the back
- Test key concepts and definitions
- Are suitable for spaced repetition

Return as JSON array:
[
    {
        "front": "Question or term",
        "back": "Answer or definition",
        "hint": "Optional hint",
        "topic": "Specific topic",
        "difficulty": "easy|medium|hard"
    }
]
"""

        query = f"Create {request.num_cards} flashcards about {request.topic} for active recall practice."

        result = await rag_engine.generate_with_rag(
            query=query,
            course_id=request.course_id,
            system_prompt=system_prompt,
            k=8,
            temperature=0.2
        )

        # Store generated flashcards
        flashcard_doc = {
            "course_id": request.course_id,
            "content_type": "flashcards",
            "generated_content": result["response"],
            "source_chunks": [s["chunk_id"] for s in result["sources"]],
            "created_at": datetime.utcnow()
        }
        flashcard_id = rag_engine.generated_content.insert_one(flashcard_doc).inserted_id

        return {
            "flashcard_id": str(flashcard_id),
            "flashcards": result["response"],
            "sources": result["sources"]
        }

    except Exception as e:
        logger.error(f"Error generating flashcards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate flashcards: {str(e)}"
        )


@router.post(
    "/generate-lesson-plan",
    summary="Generate lesson plan",
    description="Generate a structured lesson plan for a topic"
)
async def generate_lesson_plan(request: LessonPlanRequest):
    """Generate a structured lesson plan"""

    try:
        system_prompt = """You are an expert educator creating lesson plans.

Create a detailed lesson plan with:
- Learning objectives
- Time allocation for each activity
- Key concepts to cover
- Teaching methods
- Practice problems
- Assessment strategy

Format as structured JSON."""

        query = f"""Create a {request.duration_minutes}-minute lesson plan on {request.topic}.
Difficulty level: {request.difficulty}

Include:
- Learning objectives (3-5)
- Introduction (5 min)
- Main content with activities
- Practice problems
- Wrap-up and assessment
- Resources from course materials"""

        result = await rag_engine.generate_with_rag(
            query=query,
            course_id=request.course_id,
            system_prompt=system_prompt,
            k=10,
            temperature=0.4
        )

        # Store lesson plan
        plan_doc = {
            "course_id": request.course_id,
            "content_type": "lesson_plan",
            "generated_content": result["response"],
            "source_chunks": [s["chunk_id"] for s in result["sources"]],
            "created_at": datetime.utcnow()
        }
        plan_id = rag_engine.generated_content.insert_one(plan_doc).inserted_id

        return {
            "lesson_plan_id": str(plan_id),
            "lesson_plan": result["response"],
            "sources": result["sources"]
        }

    except Exception as e:
        logger.error(f"Error generating lesson plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate lesson plan: {str(e)}"
        )


@router.post(
    "/generate-semester-plan",
    summary="Generate semester study plan",
    description="Generate comprehensive semester-long study plan with ZPD and spaced repetition"
)
async def generate_semester_plan(request: SemesterPlanRequest):
    """Generate comprehensive semester study plan"""

    try:
        # Calculate number of weeks
        start = datetime.fromisoformat(request.start_date)
        end = datetime.fromisoformat(request.end_date)
        exam = datetime.fromisoformat(request.exam_date)
        num_weeks = (end - start).days // 7

        # Multi-query retrieval for comprehensive planning
        queries = [
            "course syllabus topics schedule",
            "learning objectives outcomes",
            "weekly topics progression",
            "exam preparation topics",
            *request.learning_goals
        ]

        all_chunks = await rag_engine.multi_query_retrieval(
            queries=queries,
            course_id=request.course_id,
            k_per_query=8
        )

        # Build comprehensive context
        context = "\n\n".join([
            f"[{chunk['source_file']} - Score: {chunk['score']:.3f}]\n{chunk['content']}"
            for chunk in all_chunks[:20]  # Top 20 chunks
        ])

        system_prompt = """You are an expert educational planner creating semester-long study plans.

Design plans that:
- Follow Vygotsky's Zone of Proximal Development
- Implement spaced repetition (review past material regularly)
- Build complexity progressively
- Include milestone assessments
- Balance new learning with review
- Prepare students systematically for exams

Format as structured JSON with weekly breakdown."""

        user_prompt = f"""Create a {num_weeks}-week semester study plan.

COURSE MATERIALS:
{context}

STUDENT PROFILE:
- Study hours per week: {request.study_hours_per_week}
- Learning goals: {', '.join(request.learning_goals)}
- Exam date: {exam.strftime('%B %d, %Y')}

PLAN REQUIREMENTS:
Week-by-week schedule with:
- Topics to cover (aligned with syllabus)
- ZPD level (foundational → intermediate → advanced)
- Spaced repetition schedule (which topics to review)
- Practice problems
- Checkpoint assessments every 2-3 weeks
- Final 2-3 weeks: intensive exam preparation

Format as JSON:
{{
    "weeks": [
        {{
            "week": 1,
            "dates": "Jan 15-21",
            "topics": ["Topic 1", "Topic 2"],
            "zpd_level": "foundational",
            "study_hours": 10,
            "activities": ["reading", "practice"],
            "spaced_repetition": [],
            "checkpoint": false
        }}
    ],
    "exam_prep_timeline": {{
        "week_minus_3": "...",
        "week_minus_2": "...",
        "week_minus_1": "..."
    }}
}}
"""

        # Generate with higher token limit
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = rag_engine.azure_client.chat.completions.create(
            model=rag_engine.chat_model,
            messages=messages,
            temperature=0.5,
            max_tokens=3000
        )

        # Store plan
        plan_doc = {
            "course_id": request.course_id,
            "student_id": request.student_id,
            "content_type": "semester_plan",
            "start_date": start,
            "end_date": end,
            "exam_date": exam,
            "plan": response.choices[0].message.content,
            "source_chunks": [str(chunk["_id"]) for chunk in all_chunks],
            "created_at": datetime.utcnow()
        }
        plan_id = rag_engine.semester_plans.insert_one(plan_doc).inserted_id

        return {
            "plan_id": str(plan_id),
            "semester_plan": response.choices[0].message.content,
            "num_weeks": num_weeks,
            "sources": [
                {
                    "source_file": chunk["source_file"],
                    "relevance": chunk["score"]
                }
                for chunk in all_chunks[:10]
            ]
        }

    except Exception as e:
        logger.error(f"Error generating semester plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate semester plan: {str(e)}"
        )


@router.post(
    "/generate-practice-exam",
    summary="Generate practice exam",
    description="Generate comprehensive practice exam covering multiple topics"
)
async def generate_practice_exam(request: PracticeExamRequest):
    """Generate comprehensive practice exam"""

    try:
        # Multi-query retrieval across all topics
        all_chunks = await rag_engine.multi_query_retrieval(
            queries=request.topics,
            course_id=request.course_id,
            k_per_query=10,
            filters={
                "metadata.exam_relevant": True,
                "doc_type": {"$in": ["lecture_notes", "textbook", "exam"]}
            }
        )

        # Build context
        context = "\n\n".join([
            f"[Topic: {chunk['metadata'].get('topic', 'Unknown')} - {chunk['source_file']}]\n{chunk['content']}"
            for chunk in all_chunks[:25]
        ])

        system_prompt = """You are an expert educator creating practice exams.

Generate questions that:
- Test deep understanding across cognitive levels (Bloom's Taxonomy)
- Cover all specified topics proportionally
- Match the difficulty distribution
- Include diverse question types
- Provide detailed solutions
- Reference course materials

Format as structured JSON with complete exam."""

        user_prompt = f"""Create a practice exam with {request.num_questions} questions.

COURSE MATERIALS:
{context}

EXAM SPECIFICATIONS:
- Topics: {', '.join(request.topics)}
- Difficulty distribution: {request.difficulty_distribution}
- Question types: {', '.join(request.question_types)}

For EACH question provide:
{{
    "question_number": 1,
    "question_text": "...",
    "type": "multiple_choice|short_answer|problem_solving",
    "topic": "specific topic",
    "difficulty": "easy|medium|hard",
    "points": 5,
    "options": ["A", "B", "C", "D"],  // if multiple choice
    "correct_answer": "B" or "detailed answer",
    "solution_steps": ["step 1", "step 2"],
    "explanation": "Why this is correct...",
    "source_reference": "Lecture 3, page 15"
}}

Format as JSON array of questions."""

        # Generate exam
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = rag_engine.azure_client.chat.completions.create(
            model=rag_engine.chat_model,
            messages=messages,
            temperature=0.4,
            max_tokens=3500
        )

        # Store exam
        exam_doc = {
            "course_id": request.course_id,
            "content_type": "practice_exam",
            "topics": request.topics,
            "exam": response.choices[0].message.content,
            "source_chunks": [str(chunk["_id"]) for chunk in all_chunks],
            "created_at": datetime.utcnow()
        }
        exam_id = rag_engine.generated_content.insert_one(exam_doc).inserted_id

        return {
            "exam_id": str(exam_id),
            "practice_exam": response.choices[0].message.content,
            "sources": [
                {
                    "topic": chunk["metadata"].get("topic"),
                    "source": chunk["source_file"]
                }
                for chunk in all_chunks[:15]
            ]
        }

    except Exception as e:
        logger.error(f"Error generating practice exam: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate practice exam: {str(e)}"
        )


# ============================================================================
# Administrative Endpoints
# ============================================================================

@router.post(
    "/reprocess-transcription",
    summary="Reprocess existing transcription",
    description="Reprocess an existing OCR transcription for RAG"
)
async def reprocess_transcription(request: ReprocessRequest):
    """Reprocess an existing transcription for RAG"""

    try:
        result = await reprocess_document(
            transcription_id=request.transcription_id,
            course_id=request.course_id,
            doc_type=request.doc_type
        )

        if result:
            return {
                "success": True,
                "message": f"Transcription {request.transcription_id} reprocessed successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcription {request.transcription_id} not found or processing failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing transcription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess transcription: {str(e)}"
        )


@router.post(
    "/batch-process",
    summary="Batch process transcriptions",
    description="Process multiple existing transcriptions for RAG"
)
async def batch_process(request: BatchProcessRequest, background_tasks: BackgroundTasks):
    """Batch process existing transcriptions"""

    try:
        # Run in background
        background_tasks.add_task(
            batch_process_transcriptions,
            course_id=request.course_id,
            user_id=request.user_id,
            limit=request.limit
        )

        return {
            "status": "processing",
            "message": f"Batch processing started for course {request.course_id}",
            "limit": request.limit
        }

    except Exception as e:
        logger.error(f"Error starting batch process: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start batch process: {str(e)}"
        )


# ============================================================================
# Health Check
# ============================================================================

@router.get(
    "/health",
    summary="RAG system health check",
    description="Check if RAG system components are operational"
)
async def rag_health_check():
    """Check if RAG system is operational"""

    try:
        health = rag_engine.health_check()

        if health["status"] == "healthy":
            return health
        else:
            return {
                **health,
                "warning": "Some components are not fully operational"
            }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG system unhealthy: {str(e)}"
        )

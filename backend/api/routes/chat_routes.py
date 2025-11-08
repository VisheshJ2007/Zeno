"""
Chat API Routes
Chat endpoints with RAG and educational guardrails integration
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
import logging

from ..rag.models import ChatRequest, ChatMessage
from ..rag.rag_engine import rag_engine
from ..guardrails.middleware import guardrails

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post(
    "/",
    summary="Chat with AI tutor",
    description="Chat with AI tutor using RAG and educational guardrails"
)
async def chat_with_tutor(request: ChatRequest):
    """
    Chat with AI tutor using RAG + educational guardrails

    This endpoint:
    1. Applies input guardrails to detect homework/exam cheating
    2. If inappropriate, returns educational guidance
    3. Otherwise, uses RAG to generate helpful response
    4. Applies output guardrails to verify response quality
    """

    try:
        # 1. Apply input guardrails
        guardrail_check = await guardrails.apply_guardrails(
            user_input=request.message,
            context={"course_id": request.course_id}
        )

        # 2. If guardrails triggered (homework/exam question detected)
        if not guardrail_check["allowed"]:
            logger.info(
                f"Guardrails triggered for course {request.course_id}: "
                f"{guardrail_check['triggered_rails']}"
            )

            return {
                "response": guardrail_check["educational_guidance"],
                "type": "guardrail_response",
                "triggered_rails": guardrail_check["triggered_rails"],
                "sources": []
            }

        # 3. Proceed with RAG for appropriate questions
        system_prompt = """You are Zeno, an AI tutoring assistant for college students.

Your mission: Guide students to understanding through Socratic questioning.

ALWAYS:
- Ask guiding questions rather than giving direct answers
- Provide conceptual explanations
- Celebrate student effort and reasoning
- Reference course materials for self-study
- Break complex problems into manageable steps
- Encourage active problem-solving

NEVER:
- Solve homework problems completely
- Give direct exam answers
- Do assignments for students
- Skip the learning process

Be supportive, encouraging, and educational. Focus on helping students learn HOW to solve problems, not just getting the answer."""

        result = await rag_engine.generate_with_rag(
            query=request.message,
            course_id=request.course_id,
            system_prompt=system_prompt,
            k=5,
            temperature=0.5
        )

        # 4. Apply output guardrails (check if we accidentally gave direct answer)
        output_check = await guardrails.apply_guardrails(
            user_input=result["response"],
            context={"original_query": request.message}
        )

        # Use output guardrail response if it modified anything
        final_response = output_check["response"]

        return {
            "response": final_response,
            "type": "rag_response",
            "sources": result["sources"],
            "triggered_rails": output_check["triggered_rails"],
            "usage": result.get("usage", {})
        }

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.post(
    "/simple",
    summary="Simple chat without RAG",
    description="Chat without RAG retrieval (just LLM + guardrails)"
)
async def simple_chat(request: ChatRequest):
    """
    Simple chat without RAG retrieval
    Useful for general tutoring questions not specific to course materials
    """

    try:
        # Apply guardrails
        guardrail_check = await guardrails.apply_guardrails(
            user_input=request.message,
            context={"course_id": request.course_id}
        )

        if not guardrail_check["allowed"]:
            return {
                "response": guardrail_check["educational_guidance"],
                "type": "guardrail_response",
                "triggered_rails": guardrail_check["triggered_rails"]
            }

        # Simple LLM response without RAG
        if not rag_engine.azure_client:
            return {
                "response": "Azure OpenAI is not configured.",
                "type": "error"
            }

        system_prompt = """You are Zeno, an AI tutoring assistant.
Guide students to understanding through Socratic questioning.
Never give direct answers to homework or exam questions."""

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history
        for msg in request.conversation_history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add current message
        messages.append({
            "role": "user",
            "content": request.message
        })

        response = rag_engine.azure_client.chat.completions.create(
            model=rag_engine.chat_model,
            messages=messages,
            temperature=0.6,
            max_tokens=1000
        )

        return {
            "response": response.choices[0].message.content,
            "type": "simple_chat",
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }

    except Exception as e:
        logger.error(f"Error in simple chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simple chat failed: {str(e)}"
        )


@router.get(
    "/guardrails/health",
    summary="Check guardrails status",
    description="Check if educational guardrails are enabled and working"
)
async def guardrails_health():
    """Check guardrails health status"""

    try:
        health = guardrails.health_check()
        return health
    except Exception as e:
        logger.error(f"Guardrails health check failed: {e}")
        return {
            "enabled": False,
            "status": "error",
            "error": str(e)
        }


@router.post(
    "/test-guardrails",
    summary="Test guardrails",
    description="Test educational guardrails with a sample message"
)
async def test_guardrails(message: str):
    """
    Test guardrails with a sample message
    Useful for debugging and testing guardrail behavior
    """

    try:
        result = await guardrails.apply_guardrails(message)

        return {
            "input": message,
            "guardrail_result": result,
            "interpretation": {
                "would_be_blocked": not result["allowed"],
                "triggered_any_rails": len(result["triggered_rails"]) > 0,
                "rails_triggered": result["triggered_rails"]
            }
        }

    except Exception as e:
        logger.error(f"Error testing guardrails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Guardrail test failed: {str(e)}"
        )

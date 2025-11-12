"""
Educational Guardrails Middleware
NeMo Guardrails integration for preventing homework/exam cheating
"""

from typing import Dict, Optional, Any
import os
import logging

logger = logging.getLogger(__name__)

# Try to import nemoguardrails, but don't fail if it's not installed
try:
    from nemoguardrails import RailsConfig, LLMRails
    NEMO_GUARDRAILS_AVAILABLE = True
except ImportError:
    NEMO_GUARDRAILS_AVAILABLE = False
    logger.warning(
        "NeMo Guardrails not installed. Guardrails will be disabled. "
        "Install with: pip install nemoguardrails"
    )


class EducationalGuardrails:
    """
    NeMo Guardrails integration for educational integrity
    Prevents homework/exam cheating while maintaining helpfulness
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize guardrails with Colang configuration

        Args:
            config_path: Path to guardrails configuration directory
        """
        self.enabled = False
        self.rails = None

        if not NEMO_GUARDRAILS_AVAILABLE:
            logger.warning("NeMo Guardrails not available - guardrails disabled")
            return

        try:
            # Default config path
            if config_path is None:
                config_path = os.path.join(
                    os.path.dirname(__file__),
                    "config"
                )

            logger.info(f"Loading guardrails config from: {config_path}")

            # Load configuration
            config = RailsConfig.from_path(config_path)
            self.rails = LLMRails(config)
            self.enabled = True

            logger.info("✓ Educational guardrails loaded successfully")

        except Exception as e:
            logger.error(f"⚠️  Failed to load guardrails: {e}")
            logger.warning("Guardrails will be disabled")
            self.enabled = False

    async def apply_guardrails(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Apply educational guardrails to user input

        Args:
            user_input: User's message/query
            context: Optional context (course_id, etc.)

        Returns:
            {
                "allowed": bool,
                "response": str,  # Modified/safe response
                "triggered_rails": List[str],
                "educational_guidance": Optional[str]
            }
        """

        # If guardrails not enabled, allow everything
        if not self.enabled:
            return {
                "allowed": True,
                "response": user_input,
                "triggered_rails": [],
                "educational_guidance": None
            }

        try:
            # Process through guardrails
            result = await self.rails.generate_async(
                messages=[{
                    "role": "user",
                    "content": user_input
                }],
                context=context or {}
            )

            # Extract triggered rails if available
            triggered = result.get("triggered_rails", [])

            # Check which rails were triggered
            homework_rails = [
                "prevent_homework_cheating",
                "prevent_exam_cheating",
                "prevent_direct_answers"
            ]

            is_inappropriate = any(
                rail in triggered
                for rail in homework_rails
            )

            # Check for keywords if rails didn't catch it
            if not is_inappropriate:
                is_inappropriate = self._check_inappropriate_keywords(user_input)

            return {
                "allowed": not is_inappropriate,
                "response": result.get("content", user_input),
                "triggered_rails": triggered,
                "educational_guidance": result.get("content") if is_inappropriate else None
            }

        except Exception as e:
            logger.error(f"Guardrails error: {e}")
            # Fail open - allow request but log error
            return {
                "allowed": True,
                "response": user_input,
                "triggered_rails": [],
                "educational_guidance": None,
                "error": str(e)
            }

    def _check_inappropriate_keywords(self, text: str) -> bool:
        """
        Simple keyword-based check for inappropriate requests
        Fallback when NeMo Guardrails doesn't catch it

        Args:
            text: User input text

        Returns:
            True if inappropriate, False otherwise
        """

        text_lower = text.lower()

        # Homework/assignment keywords
        homework_keywords = [
            "do my homework",
            "solve this homework",
            "homework solution",
            "assignment answer",
            "do this problem for me",
            "complete this assignment"
        ]

        # Exam/test keywords
        exam_keywords = [
            "exam answer",
            "test answer",
            "quiz solution",
            "what's on the exam",
            "exam questions",
            "test solutions"
        ]

        # Direct answer keywords
        direct_keywords = [
            "just give me the answer",
            "tell me the solution",
            "skip the explanation",
            "final answer",
            "don't explain just solve"
        ]

        all_keywords = homework_keywords + exam_keywords + direct_keywords

        return any(keyword in text_lower for keyword in all_keywords)

    def get_educational_response(self, detected_type: str) -> str:
        """
        Get appropriate educational response based on detected request type

        Args:
            detected_type: Type of inappropriate request (homework, exam, direct)

        Returns:
            Educational guidance message
        """

        responses = {
            "homework": (
                "I notice you're working on a homework problem! "
                "I can't give you the direct answer, but I'd love to help you learn. "
                "Can you tell me:\n"
                "1. What have you tried so far?\n"
                "2. What concepts do you think apply here?\n"
                "3. Where are you getting stuck?"
            ),
            "exam": (
                "I can't provide exam answers, but I can help you prepare! "
                "Let's review the concepts you'll need:\n"
                "1. What topics will be covered?\n"
                "2. Which concepts do you find challenging?\n"
                "3. Would you like to work through practice problems together?"
            ),
            "direct": (
                "I'm here to help you learn, not just provide answers! "
                "Understanding the process is more valuable than knowing the answer. "
                "Let's break this down:\n"
                "1. What is this problem asking?\n"
                "2. What concepts or formulas might help?\n"
                "3. Can you try the first step?"
            )
        }

        return responses.get(detected_type, responses["direct"])

    def health_check(self) -> Dict[str, Any]:
        """
        Check guardrails health status

        Returns:
            Health status dictionary
        """

        return {
            "enabled": self.enabled,
            "nemo_available": NEMO_GUARDRAILS_AVAILABLE,
            "rails_loaded": self.rails is not None,
            "status": "healthy" if self.enabled else "disabled"
        }


# Global instance
guardrails = EducationalGuardrails()

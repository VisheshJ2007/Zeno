"""
Question Bank Manager
Handles question storage, performance tracking, and RAG-based generation
"""

from typing import List, Dict, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging
import json

from ..rag.rag_engine import rag_engine

logger = logging.getLogger(__name__)


class QuestionBankManager:
    """Manages question bank with performance analytics"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.questions_collection: AsyncIOMotorCollection = db["question_bank"]
        self.cards_collection: AsyncIOMotorCollection = db["student_cards"]

    async def create_question(
        self,
        course_id: str,
        question_text: str,
        question_type: str,
        correct_answer: str,
        explanation: str,
        topics: List[str],
        options: Optional[List[str]] = None,
        hint: Optional[str] = None,
        skills_tested: List[str] = [],
        difficulty_rated: str = "medium",
        bloom_level: str = "understand",
        source_materials: List[str] = []
    ) -> str:
        """
        Create a new question in the bank

        Returns:
            question_id
        """
        question_doc = {
            "course_id": course_id,
            "question_text": question_text,
            "question_type": question_type,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "hint": hint,
            "topics": topics,
            "skills_tested": skills_tested,
            "difficulty_rated": difficulty_rated,
            "bloom_level": bloom_level,
            "times_presented": 0,
            "correct_responses": 0,
            "accuracy_rate": 0.0,
            "average_time_seconds": 0.0,
            "difficulty_actual": None,
            "discrimination_index": None,
            "distractor_stats": {},
            "source_materials": source_materials,
            "generated_by_rag": False,
            "created_at": datetime.utcnow(),
            "last_calibrated": None
        }

        result = await self.questions_collection.insert_one(question_doc)
        question_id = str(result.inserted_id)

        logger.info(f"Created question {question_id} for course {course_id}")
        return question_id

    async def generate_questions_with_rag(
        self,
        course_id: str,
        topics: List[str],
        num_questions_per_topic: int = 5,
        difficulty_distribution: Dict[str, float] = None,
        question_types: List[str] = None
    ) -> List[str]:
        """
        Generate questions using RAG from course materials

        Returns:
            List of created question_ids
        """
        if difficulty_distribution is None:
            difficulty_distribution = {"easy": 0.3, "medium": 0.5, "hard": 0.2}

        if question_types is None:
            question_types = ["multiple_choice"]

        created_question_ids = []

        for topic in topics:
            # Calculate questions per difficulty
            num_easy = int(num_questions_per_topic * difficulty_distribution.get("easy", 0.3))
            num_medium = int(num_questions_per_topic * difficulty_distribution.get("medium", 0.5))
            num_hard = num_questions_per_topic - num_easy - num_medium

            for difficulty, count in [("easy", num_easy), ("medium", num_medium), ("hard", num_hard)]:
                if count == 0:
                    continue

                # Generate questions via RAG
                system_prompt = """You are an expert educator creating assessment questions.

Generate questions that:
- Test conceptual understanding and application
- Are clear, specific, and unambiguous
- Have plausible distractors for multiple choice
- Include detailed explanations
- Align with Bloom's taxonomy levels

Return as JSON array of question objects."""

                user_prompt = f"""Generate {count} {difficulty} multiple-choice questions about {topic}.

Each question should be a JSON object with:
{{
    "question_text": "Clear question text",
    "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option"],
    "correct_answer": "B) Second option",
    "explanation": "Why this is correct and others are wrong",
    "hint": "Optional hint",
    "bloom_level": "remember|understand|apply|analyze|evaluate|create"
}}

Requirements:
- Difficulty: {difficulty}
- Topic: {topic}
- Format: JSON array

Return ONLY valid JSON array."""

                try:
                    result = await rag_engine.generate_with_rag(
                        query=user_prompt,
                        course_id=course_id,
                        system_prompt=system_prompt,
                        k=8,
                        filters={"metadata.topic": topic} if topic != "general" else None,
                        temperature=0.4,
                        max_tokens=2000
                    )

                    # Parse generated questions
                    try:
                        # Try to extract JSON from response
                        response_text = result["response"]

                        # Find JSON array in response
                        start_idx = response_text.find("[")
                        end_idx = response_text.rfind("]") + 1

                        if start_idx != -1 and end_idx > start_idx:
                            json_text = response_text[start_idx:end_idx]
                            questions_data = json.loads(json_text)

                            # Store each generated question
                            for q_data in questions_data:
                                # Get source materials from RAG
                                source_chunks = [s["chunk_id"] for s in result["sources"]]

                                question_id = await self.create_question(
                                    course_id=course_id,
                                    question_text=q_data["question_text"],
                                    question_type="multiple_choice",
                                    correct_answer=q_data["correct_answer"],
                                    explanation=q_data["explanation"],
                                    topics=[topic],
                                    options=q_data.get("options", []),
                                    hint=q_data.get("hint"),
                                    skills_tested=[],
                                    difficulty_rated=difficulty,
                                    bloom_level=q_data.get("bloom_level", "understand"),
                                    source_materials=source_chunks
                                )

                                # Mark as RAG-generated
                                await self.questions_collection.update_one(
                                    {"_id": question_id},
                                    {"$set": {"generated_by_rag": True}}
                                )

                                created_question_ids.append(question_id)

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse generated questions JSON: {e}")
                        logger.error(f"Response: {result['response'][:500]}")

                except Exception as e:
                    logger.error(f"Failed to generate questions for topic {topic}: {e}")

        logger.info(f"Generated {len(created_question_ids)} questions via RAG")
        return created_question_ids

    async def update_question_performance(
        self,
        question_id: str,
        is_correct: bool,
        time_spent_seconds: int,
        selected_answer: Optional[str] = None
    ):
        """
        Update question performance statistics

        Args:
            question_id: Question ID
            is_correct: Whether answered correctly
            time_spent_seconds: Time spent
            selected_answer: Answer selected (for distractor analysis)
        """
        question = await self.questions_collection.find_one({"question_id": question_id})

        if not question:
            logger.warning(f"Question {question_id} not found")
            return

        # Update counts
        times_presented = question["times_presented"] + 1
        correct_responses = question["correct_responses"] + (1 if is_correct else 0)
        accuracy_rate = (correct_responses / times_presented) * 100

        # Update average time
        total_time = question["average_time_seconds"] * question["times_presented"]
        average_time = (total_time + time_spent_seconds) / times_presented

        update_data = {
            "times_presented": times_presented,
            "correct_responses": correct_responses,
            "accuracy_rate": accuracy_rate,
            "average_time_seconds": average_time
        }

        # Update distractor stats for multiple choice
        if selected_answer and question["question_type"] == "multiple_choice":
            distractor_stats = question.get("distractor_stats", {})

            if selected_answer not in distractor_stats:
                distractor_stats[selected_answer] = {
                    "selected_count": 0,
                    "is_correct": selected_answer == question["correct_answer"]
                }

            distractor_stats[selected_answer]["selected_count"] += 1
            update_data["distractor_stats"] = distractor_stats

        # Calibrate difficulty using IRT if enough data
        if times_presented >= 10:
            # Simple IRT difficulty: logit of accuracy
            # Higher difficulty = lower accuracy
            import math
            try:
                difficulty_actual = -math.log(accuracy_rate / (100 - accuracy_rate))
                update_data["difficulty_actual"] = difficulty_actual
                update_data["last_calibrated"] = datetime.utcnow()
            except (ValueError, ZeroDivisionError):
                pass  # Skip if accuracy is 0% or 100%

        await self.questions_collection.update_one(
            {"question_id": question_id},
            {"$set": update_data}
        )

    async def get_questions_by_topic(
        self,
        course_id: str,
        topic: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get questions for a specific topic"""
        questions = await self.questions_collection.find({
            "course_id": course_id,
            "topics": topic
        }).limit(limit).to_list(length=limit)

        return questions

    async def get_questions_by_skills(
        self,
        course_id: str,
        skill_ids: List[str],
        limit: int = 50
    ) -> List[Dict]:
        """Get questions that test specific skills"""
        questions = await self.questions_collection.find({
            "course_id": course_id,
            "skills_tested": {"$in": skill_ids}
        }).limit(limit).to_list(length=limit)

        return questions

    async def get_question_statistics(
        self,
        course_id: str
    ) -> Dict:
        """Get overall question bank statistics"""
        pipeline = [
            {"$match": {"course_id": course_id}},
            {
                "$group": {
                    "_id": None,
                    "total_questions": {"$sum": 1},
                    "total_presentations": {"$sum": "$times_presented"},
                    "average_accuracy": {"$avg": "$accuracy_rate"},
                    "by_difficulty": {
                        "$push": {
                            "difficulty": "$difficulty_rated",
                            "accuracy": "$accuracy_rate"
                        }
                    },
                    "by_topic": {
                        "$push": {
                            "topics": "$topics",
                            "accuracy": "$accuracy_rate"
                        }
                    }
                }
            }
        ]

        result = await self.questions_collection.aggregate(pipeline).to_list(length=1)

        if not result:
            return {
                "total_questions": 0,
                "total_presentations": 0,
                "average_accuracy": 0.0
            }

        return result[0]

    async def link_questions_to_skills(
        self,
        question_ids: List[str],
        skill_ids: List[str]
    ) -> int:
        """Link questions to skills"""
        result = await self.questions_collection.update_many(
            {"question_id": {"$in": question_ids}},
            {"$addToSet": {"skills_tested": {"$each": skill_ids}}}
        )

        return result.modified_count

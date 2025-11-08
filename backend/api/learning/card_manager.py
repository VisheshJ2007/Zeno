"""
Student Card Manager
Handles card enrollment, review scheduling, and FSRS integration
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging

from .fsrs import FSRSScheduler, FSRSCard, Rating, rating_from_int, create_new_card
from .models import (
    StudentCard,
    ReviewHistory,
    FSRSParameters as FSRSParametersModel
)

logger = logging.getLogger(__name__)


class CardManager:
    """Manages student cards and spaced repetition scheduling"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.cards_collection: AsyncIOMotorCollection = db["student_cards"]
        self.questions_collection: AsyncIOMotorCollection = db["question_bank"]
        self.scheduler = FSRSScheduler()

    async def enroll_student_in_cards(
        self,
        student_id: str,
        course_id: str,
        question_ids: List[str]
    ) -> List[str]:
        """
        Enroll a student in a set of cards (questions)

        Returns:
            List of created card IDs
        """
        created_card_ids = []

        for question_id in question_ids:
            # Get question details
            question = await self.questions_collection.find_one(
                {"question_id": question_id}
            )

            if not question:
                logger.warning(f"Question {question_id} not found, skipping")
                continue

            # Check if already enrolled
            existing = await self.cards_collection.find_one({
                "student_id": student_id,
                "content_ref": question_id
            })

            if existing:
                logger.info(f"Student {student_id} already enrolled in {question_id}")
                continue

            # Create new card with FSRS defaults
            fsrs_card = create_new_card()

            card_data = {
                "student_id": student_id,
                "course_id": course_id,
                "content_type": question["question_type"],
                "content_ref": question_id,
                "fsrs_params": fsrs_card.to_dict(),
                "next_review": datetime.utcnow(),  # Available immediately
                "due": True,
                "topic": question["topics"][0] if question["topics"] else "general",
                "skills": question.get("skills_tested", []),
                "difficulty_rated": question.get("difficulty_rated", "medium"),
                "review_history": [],
                "total_reviews": 0,
                "correct_reviews": 0,
                "accuracy_rate": 0.0,
                "average_time_seconds": 0.0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            result = await self.cards_collection.insert_one(card_data)
            card_data["card_id"] = str(result.inserted_id)
            created_card_ids.append(card_data["card_id"])

            logger.info(f"Enrolled student {student_id} in card {card_data['card_id']}")

        return created_card_ids

    async def review_card(
        self,
        card_id: str,
        student_id: str,
        rating: int,
        time_spent_seconds: int
    ) -> Tuple[Dict, Dict]:
        """
        Process a card review with FSRS scheduling

        Args:
            card_id: Card to review
            student_id: Student performing review
            rating: Rating (1-4)
            time_spent_seconds: Time taken

        Returns:
            (updated_card, next_review_info)
        """
        # Get card
        card_doc = await self.cards_collection.find_one({
            "_id": card_id,
            "student_id": student_id
        })

        if not card_doc:
            raise ValueError(f"Card {card_id} not found for student {student_id}")

        # Convert to FSRS card
        fsrs_card = FSRSCard.from_dict(card_doc["fsrs_params"])

        # Process review with FSRS
        rating_enum = rating_from_int(rating)
        updated_fsrs_card, next_review_date = self.scheduler.review_card(
            fsrs_card,
            rating_enum,
            datetime.utcnow()
        )

        # Determine if correct (rating >= 3)
        is_correct = rating >= 3

        # Update statistics
        total_reviews = card_doc["total_reviews"] + 1
        correct_reviews = card_doc["correct_reviews"] + (1 if is_correct else 0)
        accuracy_rate = (correct_reviews / total_reviews) * 100

        # Update average time
        total_time = card_doc["average_time_seconds"] * card_doc["total_reviews"]
        average_time_seconds = (total_time + time_spent_seconds) / total_reviews

        # Create review history entry
        review_entry = {
            "reviewed_at": datetime.utcnow(),
            "rating": rating,
            "time_spent_seconds": time_spent_seconds,
            "fsrs_state_before": fsrs_card.state.value,
            "fsrs_state_after": updated_fsrs_card.state.value,
            "interval_days": updated_fsrs_card.scheduled_days,
            "stability": updated_fsrs_card.stability,
            "difficulty": updated_fsrs_card.difficulty
        }

        # Update card in database
        update_result = await self.cards_collection.update_one(
            {"_id": card_id, "student_id": student_id},
            {
                "$set": {
                    "fsrs_params": updated_fsrs_card.to_dict(),
                    "next_review": next_review_date,
                    "due": False,  # No longer due until next_review
                    "total_reviews": total_reviews,
                    "correct_reviews": correct_reviews,
                    "accuracy_rate": accuracy_rate,
                    "average_time_seconds": average_time_seconds,
                    "updated_at": datetime.utcnow()
                },
                "$push": {"review_history": review_entry}
            }
        )

        if update_result.modified_count == 0:
            raise ValueError("Failed to update card")

        # Get updated card
        updated_card = await self.cards_collection.find_one({
            "_id": card_id,
            "student_id": student_id
        })

        # Return card and next review info
        next_review_info = {
            "next_review_date": next_review_date,
            "interval_days": updated_fsrs_card.scheduled_days,
            "stability": updated_fsrs_card.stability,
            "difficulty": updated_fsrs_card.difficulty,
            "state": updated_fsrs_card.state.value
        }

        return updated_card, next_review_info

    async def get_due_cards(
        self,
        student_id: str,
        course_id: str,
        limit: int = 20,
        topics: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get cards that are due for review

        Args:
            student_id: Student ID
            course_id: Course ID
            limit: Maximum cards to return
            topics: Filter by topics (None = all topics)

        Returns:
            List of due cards with full question content
        """
        query = {
            "student_id": student_id,
            "course_id": course_id,
            "next_review": {"$lte": datetime.utcnow()}
        }

        if topics:
            query["topic"] = {"$in": topics}

        # Get due cards sorted by priority
        # Priority: cards most overdue first
        cards = await self.cards_collection.find(query).sort(
            "next_review", 1
        ).limit(limit).to_list(length=limit)

        # Enrich with question content
        enriched_cards = []
        for card in cards:
            question = await self.questions_collection.find_one({
                "question_id": card["content_ref"]
            })

            if question:
                # Merge card and question data
                enriched_card = {
                    **card,
                    "question_content": {
                        "question_text": question["question_text"],
                        "question_type": question["question_type"],
                        "options": question.get("options"),
                        "hint": question.get("hint"),
                        "explanation": question["explanation"]
                    }
                }
                enriched_cards.append(enriched_card)

        return enriched_cards

    async def get_cards_by_ids(
        self,
        card_ids: List[str],
        student_id: str
    ) -> List[Dict]:
        """Get specific cards by ID with question content"""
        cards = await self.cards_collection.find({
            "_id": {"$in": card_ids},
            "student_id": student_id
        }).to_list(length=len(card_ids))

        # Enrich with question content
        enriched_cards = []
        for card in cards:
            question = await self.questions_collection.find_one({
                "question_id": card["content_ref"]
            })

            if question:
                enriched_card = {
                    **card,
                    "question_content": {
                        "question_text": question["question_text"],
                        "question_type": question["question_type"],
                        "options": question.get("options"),
                        "hint": question.get("hint"),
                        "explanation": question["explanation"],
                        "correct_answer": question["correct_answer"]
                    }
                }
                enriched_cards.append(enriched_card)

        return enriched_cards

    async def get_due_count(
        self,
        student_id: str,
        course_id: str,
        days_ahead: int = 0
    ) -> int:
        """
        Get count of cards due now or in the next N days

        Args:
            student_id: Student ID
            course_id: Course ID
            days_ahead: Days to look ahead (0 = only today)

        Returns:
            Count of due cards
        """
        cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)

        count = await self.cards_collection.count_documents({
            "student_id": student_id,
            "course_id": course_id,
            "next_review": {"$lte": cutoff_date}
        })

        return count

    async def get_card_statistics(
        self,
        student_id: str,
        course_id: str
    ) -> Dict:
        """Get overall statistics for student's cards"""

        pipeline = [
            {"$match": {"student_id": student_id, "course_id": course_id}},
            {
                "$group": {
                    "_id": None,
                    "total_cards": {"$sum": 1},
                    "total_reviews": {"$sum": "$total_reviews"},
                    "average_accuracy": {"$avg": "$accuracy_rate"},
                    "cards_due": {
                        "$sum": {
                            "$cond": [
                                {"$lte": ["$next_review", datetime.utcnow()]},
                                1,
                                0
                            ]
                        }
                    },
                    "cards_mastered": {
                        "$sum": {
                            "$cond": [
                                {"$gte": ["$accuracy_rate", 90.0]},
                                1,
                                0
                            ]
                        }
                    }
                }
            }
        ]

        result = await self.cards_collection.aggregate(pipeline).to_list(length=1)

        if not result:
            return {
                "total_cards": 0,
                "total_reviews": 0,
                "average_accuracy": 0.0,
                "cards_due": 0,
                "cards_mastered": 0
            }

        stats = result[0]
        stats.pop("_id")
        return stats

    async def reset_card(self, card_id: str, student_id: str) -> bool:
        """Reset a card to initial state"""
        fsrs_card = create_new_card()

        result = await self.cards_collection.update_one(
            {"_id": card_id, "student_id": student_id},
            {
                "$set": {
                    "fsrs_params": fsrs_card.to_dict(),
                    "next_review": datetime.utcnow(),
                    "due": True,
                    "review_history": [],
                    "total_reviews": 0,
                    "correct_reviews": 0,
                    "accuracy_rate": 0.0,
                    "average_time_seconds": 0.0,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

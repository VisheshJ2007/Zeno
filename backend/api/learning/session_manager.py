"""
Practice Session Manager
Handles practice session creation with interleaved practice
"""

from typing import List, Dict, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import random
import logging
from collections import defaultdict

from .models import PracticeSession, SessionCardResponse

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages practice sessions with interleaved learning"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.sessions_collection: AsyncIOMotorCollection = db["practice_sessions"]
        self.cards_collection: AsyncIOMotorCollection = db["student_cards"]
        self.questions_collection: AsyncIOMotorCollection = db["question_bank"]

    def _create_interleaved_session(
        self,
        cards: List[Dict],
        target_count: int
    ) -> List[str]:
        """
        Create interleaved practice session mixing topics

        Research shows A-B-C-A-B-C is better than A-A-B-B-C-C for retention

        Args:
            cards: List of card documents
            target_count: Target number of cards

        Returns:
            List of card IDs in interleaved order
        """
        if not cards:
            return []

        # Group cards by topic
        by_topic = defaultdict(list)
        for card in cards:
            topic = card.get("topic", "general")
            by_topic[topic].append(str(card["_id"]))

        # Get list of topics
        topics = list(by_topic.keys())

        if len(topics) == 1:
            # Only one topic - return in random order
            single_topic = topics[0]
            topic_cards = by_topic[single_topic][:target_count]
            random.shuffle(topic_cards)
            return topic_cards

        # Interleave cards from different topics using round-robin
        interleaved = []
        topic_index = 0

        # Continue until we have enough cards or run out
        while len(interleaved) < target_count and any(by_topic.values()):
            # Get next topic (round-robin)
            topic = topics[topic_index % len(topics)]

            # Add a card from this topic if available
            if by_topic[topic]:
                interleaved.append(by_topic[topic].pop(0))

            topic_index += 1

            # Safety check to prevent infinite loop
            if topic_index > target_count * len(topics):
                break

        # Add 20% randomness to avoid being too predictable
        # Swap some adjacent cards randomly
        num_swaps = max(1, len(interleaved) // 10)
        for _ in range(num_swaps):
            if len(interleaved) >= 2:
                i = random.randint(0, len(interleaved) - 2)
                interleaved[i], interleaved[i + 1] = interleaved[i + 1], interleaved[i]

        return interleaved

    async def create_session(
        self,
        student_id: str,
        course_id: str,
        session_type: str = "daily_review",
        target_count: int = 20,
        topics: Optional[List[str]] = None,
        interleaved: bool = True
    ) -> Dict:
        """
        Create a new practice session

        Args:
            student_id: Student ID
            course_id: Course ID
            session_type: Type of session
            target_count: Target number of cards
            topics: Filter by topics (None = all)
            interleaved: Whether to interleave topics

        Returns:
            Session document with cards
        """
        # Build query for due cards
        query = {
            "student_id": student_id,
            "course_id": course_id,
            "next_review": {"$lte": datetime.utcnow()}
        }

        if topics:
            query["topic"] = {"$in": topics}

        # Get due cards
        cards = await self.cards_collection.find(query).sort(
            "next_review", 1  # Most overdue first
        ).limit(target_count * 2).to_list(length=target_count * 2)  # Get extra in case some filtered

        if not cards:
            return {
                "error": "No cards due for review",
                "cards_available": 0
            }

        # Select and order cards
        if interleaved and len(cards) > 1:
            card_ids = self._create_interleaved_session(cards, target_count)
        else:
            # No interleaving - just take first N cards
            card_ids = [str(card["_id"]) for card in cards[:target_count]]
            random.shuffle(card_ids)  # Random order within topics

        # Create session document
        session_doc = {
            "student_id": student_id,
            "course_id": course_id,
            "session_type": session_type,
            "interleaved": interleaved,
            "target_card_count": len(card_ids),
            "card_ids": card_ids,
            "card_responses": [],
            "current_index": 0,
            "status": "active",
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "total_time_seconds": 0,
            "cards_completed": 0,
            "cards_skipped": 0,
            "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0},
            "topic_performance": {}
        }

        result = await self.sessions_collection.insert_one(session_doc)
        session_id = str(result.inserted_id)

        # Enrich cards with question content
        enriched_cards = []
        for card_id in card_ids:
            card = await self.cards_collection.find_one({"_id": card_id})
            if card:
                question = await self.questions_collection.find_one({
                    "question_id": card["content_ref"]
                })

                if question:
                    enriched_card = {
                        "card_id": card_id,
                        "topic": card.get("topic"),
                        "difficulty": card.get("difficulty_rated"),
                        "question": {
                            "question_text": question["question_text"],
                            "question_type": question["question_type"],
                            "options": question.get("options"),
                            "hint": question.get("hint")
                        }
                    }
                    enriched_cards.append(enriched_card)

        # Calculate estimated time (2 minutes per card average)
        estimated_minutes = len(card_ids) * 2

        return {
            "session_id": session_id,
            "cards": enriched_cards,
            "total_cards": len(enriched_cards),
            "estimated_time_minutes": estimated_minutes,
            "session_type": session_type,
            "interleaved": interleaved
        }

    async def submit_card_response(
        self,
        session_id: str,
        student_id: str,
        card_id: str,
        rating: int,
        time_spent_seconds: int
    ) -> Dict:
        """
        Submit a response to a card in the session

        Args:
            session_id: Session ID
            student_id: Student ID
            card_id: Card being answered
            rating: Rating (1-4)
            time_spent_seconds: Time spent

        Returns:
            Updated session info
        """
        # Get session
        session = await self.sessions_collection.find_one({
            "_id": session_id,
            "student_id": student_id,
            "status": "active"
        })

        if not session:
            raise ValueError("Session not found or not active")

        # Verify card is in session
        if card_id not in session["card_ids"]:
            raise ValueError("Card not in this session")

        # Get card to determine topic
        card = await self.cards_collection.find_one({"_id": card_id})
        if not card:
            raise ValueError("Card not found")

        topic = card.get("topic", "general")

        # Create response entry
        response = {
            "card_id": card_id,
            "presented_at": datetime.utcnow(),
            "rating": rating,
            "time_spent_seconds": time_spent_seconds,
            "skipped": False
        }

        # Update rating distribution
        rating_key = str(rating)
        rating_dist = session.get("rating_distribution", {"1": 0, "2": 0, "3": 0, "4": 0})
        rating_dist[rating_key] = rating_dist.get(rating_key, 0) + 1

        # Update topic performance
        topic_perf = session.get("topic_performance", {})
        if topic not in topic_perf:
            topic_perf[topic] = {
                "presented": 0,
                "correct": 0,
                "total_time": 0
            }

        topic_perf[topic]["presented"] += 1
        if rating >= 3:  # Rating 3 or 4 = correct
            topic_perf[topic]["correct"] += 1
        topic_perf[topic]["total_time"] += time_spent_seconds

        # Update session
        update_result = await self.sessions_collection.update_one(
            {"_id": session_id, "student_id": student_id},
            {
                "$push": {"card_responses": response},
                "$inc": {
                    "current_index": 1,
                    "cards_completed": 1,
                    "total_time_seconds": time_spent_seconds
                },
                "$set": {
                    "rating_distribution": rating_dist,
                    "topic_performance": topic_perf
                }
            }
        )

        if update_result.modified_count == 0:
            raise ValueError("Failed to update session")

        # Get updated session
        updated_session = await self.sessions_collection.find_one({
            "_id": session_id
        })

        # Check if session is complete
        is_complete = updated_session["cards_completed"] >= len(updated_session["card_ids"])

        return {
            "session_id": session_id,
            "cards_completed": updated_session["cards_completed"],
            "total_cards": len(updated_session["card_ids"]),
            "is_complete": is_complete,
            "current_index": updated_session["current_index"]
        }

    async def complete_session(
        self,
        session_id: str,
        student_id: str
    ) -> Dict:
        """
        Mark session as complete and return summary

        Args:
            session_id: Session ID
            student_id: Student ID

        Returns:
            Session summary with statistics
        """
        # Get session
        session = await self.sessions_collection.find_one({
            "_id": session_id,
            "student_id": student_id
        })

        if not session:
            raise ValueError("Session not found")

        # Calculate final metrics
        cards_completed = session["cards_completed"]
        total_cards = len(session["card_ids"])

        # Calculate accuracy (ratings 3-4 are correct)
        correct_count = session["rating_distribution"].get("3", 0) + \
                       session["rating_distribution"].get("4", 0)
        accuracy_rate = (correct_count / cards_completed * 100) if cards_completed > 0 else 0

        # Update session status
        await self.sessions_collection.update_one(
            {"_id": session_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow()
                }
            }
        )

        # Return summary
        return {
            "session_id": session_id,
            "status": "completed",
            "cards_completed": cards_completed,
            "total_cards": total_cards,
            "accuracy_rate": round(accuracy_rate, 1),
            "total_time_seconds": session["total_time_seconds"],
            "average_time_per_card": round(
                session["total_time_seconds"] / cards_completed, 1
            ) if cards_completed > 0 else 0,
            "rating_distribution": session["rating_distribution"],
            "topic_performance": session["topic_performance"],
            "started_at": session["started_at"],
            "completed_at": datetime.utcnow()
        }

    async def get_session(
        self,
        session_id: str,
        student_id: str
    ) -> Optional[Dict]:
        """Get session details"""
        session = await self.sessions_collection.find_one({
            "_id": session_id,
            "student_id": student_id
        })

        return session

    async def get_recent_sessions(
        self,
        student_id: str,
        course_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent sessions for student"""
        sessions = await self.sessions_collection.find({
            "student_id": student_id,
            "course_id": course_id
        }).sort("started_at", -1).limit(limit).to_list(length=limit)

        return sessions

    async def get_session_statistics(
        self,
        student_id: str,
        course_id: str,
        days: int = 30
    ) -> Dict:
        """Get session statistics for the last N days"""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        pipeline = [
            {
                "$match": {
                    "student_id": student_id,
                    "course_id": course_id,
                    "started_at": {"$gte": cutoff_date},
                    "status": "completed"
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_sessions": {"$sum": 1},
                    "total_cards": {"$sum": "$cards_completed"},
                    "total_time": {"$sum": "$total_time_seconds"},
                    "total_correct": {
                        "$sum": {
                            "$add": [
                                {"$ifNull": ["$rating_distribution.3", 0]},
                                {"$ifNull": ["$rating_distribution.4", 0]}
                            ]
                        }
                    }
                }
            }
        ]

        result = await self.sessions_collection.aggregate(pipeline).to_list(length=1)

        if not result:
            return {
                "total_sessions": 0,
                "total_cards": 0,
                "total_time_minutes": 0,
                "average_accuracy": 0.0,
                "average_cards_per_session": 0
            }

        stats = result[0]
        total_cards = stats["total_cards"]
        total_correct = stats["total_correct"]

        return {
            "total_sessions": stats["total_sessions"],
            "total_cards": total_cards,
            "total_time_minutes": round(stats["total_time"] / 60, 1),
            "average_accuracy": round(
                (total_correct / total_cards * 100) if total_cards > 0 else 0, 1
            ),
            "average_cards_per_session": round(
                total_cards / stats["total_sessions"], 1
            ) if stats["total_sessions"] > 0 else 0
        }

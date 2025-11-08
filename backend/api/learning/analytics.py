"""
Analytics Manager
Tracks student performance, topic accuracy trends, and provides insights
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AnalyticsManager:
    """Manages analytics and performance tracking"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.cards_collection: AsyncIOMotorCollection = db["student_cards"]
        self.sessions_collection: AsyncIOMotorCollection = db["practice_sessions"]
        self.skills_collection: AsyncIOMotorCollection = db["skills"]
        self.progress_collection: AsyncIOMotorCollection = db["student_skill_progress"]

    async def get_topic_analytics(
        self,
        student_id: str,
        course_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Get accuracy analytics by topic over time

        Returns topic-level accuracy trends showing improvement as difficulty increases
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all cards for student
        cards = await self.cards_collection.find({
            "student_id": student_id,
            "course_id": course_id,
            "created_at": {"$gte": cutoff_date}
        }).to_list(length=None)

        # Group performance by topic
        topic_data = defaultdict(lambda: {
            "total_attempts": 0,
            "correct_attempts": 0,
            "by_difficulty": {
                "easy": {"attempts": 0, "correct": 0},
                "medium": {"attempts": 0, "correct": 0},
                "hard": {"attempts": 0, "correct": 0}
            },
            "time_series": [],
            "total_time": 0
        })

        # Process each card's review history
        for card in cards:
            topic = card.get("topic", "general")
            difficulty = card.get("difficulty_rated", "medium")

            # Process review history
            for review in card.get("review_history", []):
                rating = review["rating"]
                is_correct = rating >= 3  # Rating 3-4 = correct

                # Update totals
                topic_data[topic]["total_attempts"] += 1
                if is_correct:
                    topic_data[topic]["correct_attempts"] += 1

                # Update by difficulty
                topic_data[topic]["by_difficulty"][difficulty]["attempts"] += 1
                if is_correct:
                    topic_data[topic]["by_difficulty"][difficulty]["correct"] += 1

                # Add to time series
                topic_data[topic]["time_series"].append({
                    "date": review["reviewed_at"],
                    "correct": is_correct,
                    "difficulty": difficulty,
                    "time_spent": review["time_spent_seconds"]
                })

                topic_data[topic]["total_time"] += review["time_spent_seconds"]

        # Build analytics for each topic
        analytics = []

        for topic, data in topic_data.items():
            # Calculate overall accuracy
            overall_accuracy = (
                data["correct_attempts"] / data["total_attempts"] * 100
            ) if data["total_attempts"] > 0 else 0.0

            # Calculate accuracy by difficulty
            accuracy_by_difficulty = {}
            for diff in ["easy", "medium", "hard"]:
                diff_data = data["by_difficulty"][diff]
                accuracy_by_difficulty[diff] = (
                    diff_data["correct"] / diff_data["attempts"] * 100
                ) if diff_data["attempts"] > 0 else 0.0

            # Create time series with rolling accuracy
            # Group by week and calculate accuracy
            time_series = self._create_weekly_accuracy_trend(data["time_series"])

            # Get associated skills
            skills = await self.skills_collection.find({
                "course_id": course_id,
                "topic": topic
            }).to_list(length=None)

            skill_names = [s["name"] for s in skills]

            analytics.append({
                "topic": topic,
                "total_attempts": data["total_attempts"],
                "correct_attempts": data["correct_attempts"],
                "overall_accuracy": round(overall_accuracy, 1),
                "accuracy_by_difficulty": {
                    k: round(v, 1) for k, v in accuracy_by_difficulty.items()
                },
                "accuracy_trend": time_series,
                "average_time_seconds": round(
                    data["total_time"] / data["total_attempts"], 1
                ) if data["total_attempts"] > 0 else 0,
                "skills": skill_names
            })

        # Sort by total attempts (most practiced first)
        analytics.sort(key=lambda x: x["total_attempts"], reverse=True)

        return analytics

    def _create_weekly_accuracy_trend(
        self,
        time_series: List[Dict]
    ) -> List[Dict]:
        """
        Create weekly accuracy trend from time series data

        Shows how accuracy changes over time as difficulty increases
        """
        if not time_series:
            return []

        # Sort by date
        time_series.sort(key=lambda x: x["date"])

        # Group by week
        weekly_data = defaultdict(lambda: {
            "attempts": 0,
            "correct": 0,
            "by_difficulty": {
                "easy": {"attempts": 0, "correct": 0},
                "medium": {"attempts": 0, "correct": 0},
                "hard": {"attempts": 0, "correct": 0}
            }
        })

        for point in time_series:
            # Get week start date
            date = point["date"]
            week_start = date - timedelta(days=date.weekday())
            week_key = week_start.strftime("%Y-%m-%d")

            # Update weekly stats
            weekly_data[week_key]["attempts"] += 1
            if point["correct"]:
                weekly_data[week_key]["correct"] += 1

            # Update by difficulty
            diff = point["difficulty"]
            weekly_data[week_key]["by_difficulty"][diff]["attempts"] += 1
            if point["correct"]:
                weekly_data[week_key]["by_difficulty"][diff]["correct"] += 1

        # Convert to list with accuracy calculations
        trend = []
        for week_key in sorted(weekly_data.keys()):
            data = weekly_data[week_key]

            accuracy = (
                data["correct"] / data["attempts"] * 100
            ) if data["attempts"] > 0 else 0.0

            # Calculate predominant difficulty for this week
            diff_counts = {
                d: data["by_difficulty"][d]["attempts"]
                for d in ["easy", "medium", "hard"]
            }
            predominant_difficulty = max(diff_counts, key=diff_counts.get)

            trend.append({
                "date": week_key,
                "accuracy_rate": round(accuracy, 1),
                "attempts": data["attempts"],
                "correct": data["correct"],
                "predominant_difficulty": predominant_difficulty,
                "difficulty_breakdown": {
                    d: round(
                        data["by_difficulty"][d]["correct"] / data["by_difficulty"][d]["attempts"] * 100, 1
                    ) if data["by_difficulty"][d]["attempts"] > 0 else 0.0
                    for d in ["easy", "medium", "hard"]
                }
            })

        return trend

    async def get_student_analytics(
        self,
        student_id: str,
        course_id: str
    ) -> Dict:
        """
        Get comprehensive analytics for a student

        Returns:
            Complete analytics dashboard data
        """
        # Get card statistics
        card_stats = await self._get_card_statistics(student_id, course_id)

        # Get session statistics
        session_stats = await self._get_session_statistics(student_id, course_id)

        # Get skill progress
        skill_stats = await self._get_skill_statistics(student_id, course_id)

        # Get topic analytics
        topic_analytics = await self.get_topic_analytics(student_id, course_id, days=30)

        # Get recommended topics (topics with low accuracy)
        recommended_topics = [
            t["topic"] for t in topic_analytics
            if t["overall_accuracy"] < 70.0
        ][:3]

        # Get recommended skills
        recommended_skills = await self._get_recommended_skills(student_id, course_id)

        # Calculate streaks
        streak_days = await self._calculate_streak(student_id, course_id)

        return {
            "student_id": student_id,
            "course_id": course_id,
            "total_cards_reviewed": card_stats["total_reviews"],
            "overall_accuracy": card_stats["average_accuracy"],
            "total_time_minutes": session_stats["total_time_minutes"],
            "active_days": session_stats["active_days"],
            "current_streak_days": streak_days,
            "topic_analytics": topic_analytics,
            "skills_mastered": skill_stats["mastered"],
            "skills_in_progress": skill_stats["in_progress"],
            "skills_not_started": skill_stats["not_started"],
            "overall_mastery": skill_stats["overall_mastery"],
            "cards_due_today": card_stats["cards_due_today"],
            "cards_due_this_week": card_stats["cards_due_week"],
            "average_reviews_per_day": session_stats["avg_cards_per_day"],
            "accuracy_trend_7d": await self._get_accuracy_trend(student_id, course_id, 7),
            "accuracy_trend_30d": await self._get_accuracy_trend(student_id, course_id, 30),
            "recommended_topics": recommended_topics,
            "recommended_skills": recommended_skills
        }

    async def _get_card_statistics(
        self,
        student_id: str,
        course_id: str
    ) -> Dict:
        """Get card statistics"""
        pipeline = [
            {"$match": {"student_id": student_id, "course_id": course_id}},
            {
                "$group": {
                    "_id": None,
                    "total_cards": {"$sum": 1},
                    "total_reviews": {"$sum": "$total_reviews"},
                    "average_accuracy": {"$avg": "$accuracy_rate"},
                    "cards_due_today": {
                        "$sum": {
                            "$cond": [
                                {"$lte": ["$next_review", datetime.utcnow()]},
                                1,
                                0
                            ]
                        }
                    },
                    "cards_due_week": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$lte": [
                                        "$next_review",
                                        datetime.utcnow() + timedelta(days=7)
                                    ]
                                },
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
                "cards_due_today": 0,
                "cards_due_week": 0
            }

        stats = result[0]
        stats.pop("_id")
        return stats

    async def _get_session_statistics(
        self,
        student_id: str,
        course_id: str
    ) -> Dict:
        """Get session statistics"""
        pipeline = [
            {
                "$match": {
                    "student_id": student_id,
                    "course_id": course_id,
                    "status": "completed"
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_sessions": {"$sum": 1},
                    "total_time": {"$sum": "$total_time_seconds"},
                    "total_cards": {"$sum": "$cards_completed"},
                    "unique_days": {"$addToSet": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$started_at"}
                    }}
                }
            }
        ]

        result = await self.sessions_collection.aggregate(pipeline).to_list(length=1)

        if not result:
            return {
                "total_sessions": 0,
                "total_time_minutes": 0,
                "active_days": 0,
                "avg_cards_per_day": 0
            }

        stats = result[0]

        return {
            "total_sessions": stats["total_sessions"],
            "total_time_minutes": round(stats["total_time"] / 60, 1),
            "active_days": len(stats["unique_days"]),
            "avg_cards_per_day": round(
                stats["total_cards"] / len(stats["unique_days"]), 1
            ) if len(stats["unique_days"]) > 0 else 0
        }

    async def _get_skill_statistics(
        self,
        student_id: str,
        course_id: str
    ) -> Dict:
        """Get skill progress statistics"""
        # Get all skills
        total_skills = await self.skills_collection.count_documents({
            "course_id": course_id
        })

        # Get progress
        pipeline = [
            {"$match": {"student_id": student_id, "course_id": course_id}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "avg_mastery": {"$avg": "$mastery_level"}
                }
            }
        ]

        result = await self.progress_collection.aggregate(pipeline).to_list(length=None)

        status_counts = {r["_id"]: r["count"] for r in result}
        mastered = status_counts.get("mastered", 0)
        in_progress = status_counts.get("learning", 0) + status_counts.get("reviewing", 0)
        not_started = total_skills - mastered - in_progress

        # Overall mastery
        overall_mastery = (mastered / total_skills * 100) if total_skills > 0 else 0.0

        return {
            "mastered": mastered,
            "in_progress": in_progress,
            "not_started": not_started,
            "overall_mastery": round(overall_mastery, 1)
        }

    async def _calculate_streak(
        self,
        student_id: str,
        course_id: str
    ) -> int:
        """Calculate current streak of consecutive days with practice"""
        sessions = await self.sessions_collection.find({
            "student_id": student_id,
            "course_id": course_id,
            "status": "completed"
        }).sort("started_at", -1).to_list(length=None)

        if not sessions:
            return 0

        # Get unique practice dates
        practice_dates = set()
        for session in sessions:
            date_str = session["started_at"].strftime("%Y-%m-%d")
            practice_dates.add(date_str)

        # Sort dates descending
        sorted_dates = sorted(practice_dates, reverse=True)

        # Count consecutive days from today
        streak = 0
        current_date = datetime.utcnow().date()

        for date_str in sorted_dates:
            practice_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Check if this date is consecutive
            expected_date = current_date - timedelta(days=streak)

            if practice_date == expected_date:
                streak += 1
            elif practice_date < expected_date:
                # Gap in streak
                break

        return streak

    async def _get_accuracy_trend(
        self,
        student_id: str,
        course_id: str,
        days: int
    ) -> List[float]:
        """Get daily accuracy trend for last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        sessions = await self.sessions_collection.find({
            "student_id": student_id,
            "course_id": course_id,
            "status": "completed",
            "started_at": {"$gte": cutoff_date}
        }).sort("started_at", 1).to_list(length=None)

        # Group by day
        daily_accuracy = defaultdict(lambda: {"correct": 0, "total": 0})

        for session in sessions:
            date_key = session["started_at"].strftime("%Y-%m-%d")
            correct = session["rating_distribution"].get("3", 0) + \
                     session["rating_distribution"].get("4", 0)
            total = session["cards_completed"]

            daily_accuracy[date_key]["correct"] += correct
            daily_accuracy[date_key]["total"] += total

        # Calculate accuracy for each day
        trend = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
            if date in daily_accuracy:
                data = daily_accuracy[date]
                accuracy = (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0
                trend.append(round(accuracy, 1))
            else:
                trend.append(0.0)

        return trend

    async def _get_recommended_skills(
        self,
        student_id: str,
        course_id: str
    ) -> List[str]:
        """Get recommended skills to work on"""
        # Get skills with prerequisites met but not mastered
        all_skills = await self.skills_collection.find({
            "course_id": course_id
        }).to_list(length=None)

        progress_docs = await self.progress_collection.find({
            "student_id": student_id,
            "course_id": course_id
        }).to_list(length=None)

        progress_by_skill = {p["skill_id"]: p for p in progress_docs}

        recommendations = []

        for skill in all_skills:
            skill_id = str(skill["_id"])
            progress = progress_by_skill.get(skill_id, {})

            if progress.get("status") == "mastered":
                continue

            # Check prerequisites
            prereqs_met = all(
                progress_by_skill.get(prereq_id, {}).get("mastery_level", 0) >= 70
                for prereq_id in skill.get("prerequisites", [])
            )

            if prereqs_met:
                recommendations.append(skill["name"])

        return recommendations[:5]

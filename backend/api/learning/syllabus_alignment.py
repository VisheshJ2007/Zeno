"""
Syllabus Alignment Module
Uses RAG to cross-check course materials against syllabus
"""

from typing import List, Dict, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging

from ..rag.rag_engine import rag_engine

logger = logging.getLogger(__name__)


class SyllabusAlignmentManager:
    """Manages syllabus alignment analysis using RAG"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.syllabus_alignment_collection: AsyncIOMotorCollection = db["syllabus_alignment"]
        self.transcriptions_collection: AsyncIOMotorCollection = db["transcriptions"]
        self.skills_collection: AsyncIOMotorCollection = db["skills"]
        self.progress_collection: AsyncIOMotorCollection = db["student_skill_progress"]

    async def analyze_syllabus_coverage(
        self,
        course_id: str,
        syllabus_transcription_id: str,
        student_id: Optional[str] = None
    ) -> Dict:
        """
        Analyze how well course materials cover syllabus topics

        Args:
            course_id: Course ID
            syllabus_transcription_id: Transcription ID of syllabus document
            student_id: Optional student ID to include progress data

        Returns:
            Alignment report with coverage analysis
        """
        # Get syllabus content
        syllabus = await self.transcriptions_collection.find_one({
            "transcription_id": syllabus_transcription_id
        })

        if not syllabus:
            raise ValueError(f"Syllabus transcription {syllabus_transcription_id} not found")

        syllabus_text = syllabus["content"]["cleaned_text"]

        # Use RAG to extract topics from syllabus
        topics = await self._extract_topics_from_syllabus(course_id, syllabus_text)

        # For each topic, check coverage in course materials
        topic_coverage = []

        for topic in topics:
            # Search for materials covering this topic
            try:
                materials = await rag_engine.retrieve_relevant_chunks(
                    query=f"Materials about {topic['name']}: {topic['description']}",
                    course_id=course_id,
                    k=10
                )

                # Calculate coverage score based on:
                # - Number of materials found
                # - Relevance scores
                # - Diversity of document types

                materials_count = len(materials)
                avg_relevance = sum(m["score"] for m in materials) / len(materials) if materials else 0

                # Coverage score: 0-100
                # Good coverage = multiple materials with high relevance
                coverage_score = min(100, (materials_count * 10) + (avg_relevance * 50))

                # Get document types
                doc_types = list(set(m.get("doc_type", "unknown") for m in materials))

                # Get student progress if provided
                student_progress = 0.0
                if student_id:
                    # Find skills related to this topic
                    skills = await self.skills_collection.find({
                        "course_id": course_id,
                        "topic": topic["name"]
                    }).to_list(length=None)

                    if skills:
                        # Get progress on these skills
                        skill_ids = [str(s["_id"]) for s in skills]
                        progress_docs = await self.progress_collection.find({
                            "student_id": student_id,
                            "skill_id": {"$in": skill_ids}
                        }).to_list(length=None)

                        if progress_docs:
                            avg_mastery = sum(p["mastery_level"] for p in progress_docs) / len(progress_docs)
                            student_progress = avg_mastery

                topic_coverage.append({
                    "topic": topic["name"],
                    "description": topic["description"],
                    "materials_count": materials_count,
                    "coverage_score": round(coverage_score, 1),
                    "average_relevance": round(avg_relevance, 3),
                    "document_types": doc_types,
                    "student_progress": round(student_progress, 1) if student_id else None,
                    "sample_materials": [
                        {
                            "source_file": m["source_file"],
                            "doc_type": m.get("doc_type"),
                            "relevance": round(m["score"], 3)
                        }
                        for m in materials[:3]
                    ]
                })

            except Exception as e:
                logger.error(f"Error analyzing coverage for topic {topic['name']}: {e}")
                topic_coverage.append({
                    "topic": topic["name"],
                    "description": topic["description"],
                    "materials_count": 0,
                    "coverage_score": 0.0,
                    "error": str(e)
                })

        # Identify coverage gaps (topics with low coverage)
        coverage_gaps = [
            t["topic"] for t in topic_coverage
            if t.get("coverage_score", 0) < 50.0
        ]

        # Calculate overall coverage
        overall_coverage = sum(t.get("coverage_score", 0) for t in topic_coverage) / len(topic_coverage) \
            if topic_coverage else 0.0

        topics_covered = sum(1 for t in topic_coverage if t.get("coverage_score", 0) >= 70.0)

        # Generate recommendations
        recommendations = await self._generate_recommendations(topic_coverage, student_id)

        # Store alignment report
        alignment_doc = {
            "course_id": course_id,
            "syllabus_transcription_id": syllabus_transcription_id,
            "student_id": student_id,
            "topics": topic_coverage,
            "coverage_gaps": coverage_gaps,
            "overall_coverage": round(overall_coverage, 1),
            "topics_covered": topics_covered,
            "total_topics": len(topics),
            "recommendations": recommendations,
            "analyzed_at": datetime.utcnow()
        }

        await self.syllabus_alignment_collection.insert_one(alignment_doc)

        return alignment_doc

    async def _extract_topics_from_syllabus(
        self,
        course_id: str,
        syllabus_text: str
    ) -> List[Dict]:
        """
        Extract topics from syllabus using RAG

        Returns:
            List of topics with descriptions
        """
        system_prompt = """You are analyzing a course syllabus to extract key topics.

Extract the main topics/modules/units that will be covered in the course.

For each topic provide:
- Clear, specific name
- Brief description of what will be covered

Return as JSON array."""

        user_prompt = f"""Extract all main topics from this syllabus:

SYLLABUS:
{syllabus_text[:3000]}

Return JSON array:
[
    {{
        "name": "Topic Name",
        "description": "Brief description of what's covered"
    }}
]

Extract 5-15 main topics. Return ONLY valid JSON array."""

        try:
            result = await rag_engine.generate_with_rag(
                query=user_prompt,
                course_id=course_id,
                system_prompt=system_prompt,
                k=5,
                temperature=0.2,
                max_tokens=1500
            )

            # Parse topics
            import json
            response_text = result["response"]
            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                topics = json.loads(json_text)
                return topics
            else:
                logger.error("No JSON array found in syllabus topics response")
                return []

        except Exception as e:
            logger.error(f"Failed to extract topics from syllabus: {e}")
            # Return fallback topics
            return [
                {"name": "General Course Content", "description": "Course materials"}
            ]

    async def _generate_recommendations(
        self,
        topic_coverage: List[Dict],
        student_id: Optional[str]
    ) -> List[str]:
        """Generate recommendations based on coverage analysis"""
        recommendations = []

        # Identify low-coverage topics
        low_coverage = [t for t in topic_coverage if t.get("coverage_score", 0) < 50.0]

        if low_coverage:
            recommendations.append(
                f"Add more materials for: {', '.join(t['topic'] for t in low_coverage[:3])}"
            )

        # If student data provided, give personalized recommendations
        if student_id:
            # Identify topics with materials but low student progress
            needs_practice = [
                t for t in topic_coverage
                if t.get("coverage_score", 0) >= 70.0 and t.get("student_progress", 100) < 60.0
            ]

            if needs_practice:
                recommendations.append(
                    f"Focus practice on: {', '.join(t['topic'] for t in needs_practice[:3])}"
                )

            # Identify topics student has mastered but could review
            for_review = [
                t for t in topic_coverage
                if 80.0 <= t.get("student_progress", 0) < 95.0
            ]

            if for_review:
                recommendations.append(
                    f"Review to maintain mastery: {', '.join(t['topic'] for t in for_review[:2])}"
                )

        # Check for missing document types
        all_doc_types = set()
        for topic in topic_coverage:
            all_doc_types.update(topic.get("document_types", []))

        recommended_types = ["lecture_notes", "textbook", "exam"]
        missing_types = [t for t in recommended_types if t not in all_doc_types]

        if missing_types:
            recommendations.append(
                f"Consider adding materials of type: {', '.join(missing_types)}"
            )

        return recommendations

    async def get_latest_alignment(
        self,
        course_id: str,
        student_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Get the most recent alignment report"""
        query = {"course_id": course_id}

        if student_id:
            query["student_id"] = student_id

        alignment = await self.syllabus_alignment_collection.find_one(
            query,
            sort=[("analyzed_at", -1)]
        )

        return alignment

    async def suggest_materials_for_topic(
        self,
        course_id: str,
        topic: str,
        description: Optional[str] = None
    ) -> List[Dict]:
        """
        Suggest relevant materials from the course for a specific topic

        Returns:
            List of suggested materials with relevance scores
        """
        query = f"{topic}"
        if description:
            query += f": {description}"

        try:
            materials = await rag_engine.retrieve_relevant_chunks(
                query=query,
                course_id=course_id,
                k=10
            )

            suggestions = [
                {
                    "source_file": m["source_file"],
                    "doc_type": m.get("doc_type", "unknown"),
                    "content_preview": m["content"][:200] + "...",
                    "relevance_score": round(m["score"], 3),
                    "metadata": m.get("metadata", {})
                }
                for m in materials
            ]

            return suggestions

        except Exception as e:
            logger.error(f"Failed to suggest materials for topic {topic}: {e}")
            return []

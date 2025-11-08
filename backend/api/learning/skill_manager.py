"""
Skill Manager
Handles skill tracking, checklist generation, and progress analytics
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging
import json

from ..rag.rag_engine import rag_engine

logger = logging.getLogger(__name__)


class SkillManager:
    """Manages skills, checklists, and student progress"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.skills_collection: AsyncIOMotorCollection = db["skills"]
        self.student_progress_collection: AsyncIOMotorCollection = db["student_skill_progress"]
        self.cards_collection: AsyncIOMotorCollection = db["student_cards"]

    async def generate_skills_from_syllabus(
        self,
        course_id: str,
        syllabus_text: str,
        syllabus_transcription_id: Optional[str] = None
    ) -> List[str]:
        """
        Use RAG to extract skills from syllabus

        Returns:
            List of created skill IDs
        """
        system_prompt = """You are an expert educational planner analyzing course syllabi.

Extract learning objectives and skills from the syllabus.

For each skill provide:
- Clear, specific name
- Detailed description
- Topic category
- Difficulty level (foundational, intermediate, advanced)
- Prerequisites (which skills must be learned first)
- Estimated hours to master
- Bloom's taxonomy level

Return as JSON array."""

        user_prompt = f"""Analyze this syllabus and extract all learning skills/objectives:

SYLLABUS:
{syllabus_text[:4000]}  # Limit to avoid token limits

Return JSON array:
[
    {{
        "name": "Binary Search Trees",
        "description": "Understand and implement binary search tree data structures",
        "topic": "Data Structures",
        "difficulty": "intermediate",
        "prerequisites": ["Binary Trees", "Tree Traversals"],
        "estimated_hours": 4.0,
        "bloom_level": "apply"
    }}
]

Requirements:
- Extract 10-20 key skills
- Organize by complexity (foundational → advanced)
- Identify clear prerequisite relationships
- Use specific, measurable skill names

Return ONLY valid JSON array."""

        try:
            result = await rag_engine.generate_with_rag(
                query=user_prompt,
                course_id=course_id,
                system_prompt=system_prompt,
                k=10,
                temperature=0.3,
                max_tokens=2500
            )

            # Parse skills
            response_text = result["response"]
            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]") + 1

            if start_idx == -1 or end_idx <= start_idx:
                logger.error("No JSON array found in response")
                return []

            json_text = response_text[start_idx:end_idx]
            skills_data = json.loads(json_text)

            # Create skill documents
            created_skill_ids = []
            skill_name_to_id = {}  # For resolving prerequisites

            # First pass: create all skills
            for skill_data in skills_data:
                skill_doc = {
                    "course_id": course_id,
                    "syllabus_ref": syllabus_transcription_id,
                    "name": skill_data["name"],
                    "description": skill_data["description"],
                    "topic": skill_data["topic"],
                    "difficulty": skill_data.get("difficulty", "intermediate"),
                    "prerequisites": [],  # Will update in second pass
                    "estimated_hours": skill_data.get("estimated_hours", 2.0),
                    "source_materials": [],  # Will populate later
                    "assessment_questions": [],
                    "bloom_level": skill_data.get("bloom_level", "apply"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }

                result = await self.skills_collection.insert_one(skill_doc)
                skill_id = str(result.inserted_id)
                created_skill_ids.append(skill_id)
                skill_name_to_id[skill_data["name"]] = skill_id

                logger.info(f"Created skill: {skill_data['name']} ({skill_id})")

            # Second pass: resolve prerequisites
            for skill_data in skills_data:
                skill_name = skill_data["name"]
                skill_id = skill_name_to_id[skill_name]
                prerequisite_names = skill_data.get("prerequisites", [])

                # Convert prerequisite names to IDs
                prerequisite_ids = []
                for prereq_name in prerequisite_names:
                    if prereq_name in skill_name_to_id:
                        prerequisite_ids.append(skill_name_to_id[prereq_name])

                # Update skill with prerequisites
                await self.skills_collection.update_one(
                    {"_id": skill_id},
                    {"$set": {"prerequisites": prerequisite_ids}}
                )

            # Third pass: link to course materials via RAG
            for skill_id in created_skill_ids:
                skill = await self.skills_collection.find_one({"_id": skill_id})

                # Search for relevant materials
                try:
                    materials = await rag_engine.retrieve_relevant_chunks(
                        query=f"{skill['name']}: {skill['description']}",
                        course_id=course_id,
                        k=5
                    )

                    if materials:
                        source_materials = [
                            {
                                "doc_type": m.get("doc_type", "unknown"),
                                "chunk_ids": [str(m["_id"])]
                            }
                            for m in materials
                        ]

                        await self.skills_collection.update_one(
                            {"_id": skill_id},
                            {"$set": {"source_materials": source_materials}}
                        )
                except Exception as e:
                    logger.warning(f"Failed to link materials for skill {skill_id}: {e}")

            logger.info(f"Created {len(created_skill_ids)} skills from syllabus")
            return created_skill_ids

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse skills JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to generate skills from syllabus: {e}")
            return []

    async def get_student_checklist(
        self,
        student_id: str,
        course_id: str
    ) -> Dict:
        """
        Get skill checklist with student progress

        Returns:
            Checklist with skills organized by status
        """
        # Get all skills for course
        skills = await self.skills_collection.find({
            "course_id": course_id
        }).sort("difficulty", 1).to_list(length=None)

        # Get student progress for all skills
        progress_docs = await self.student_progress_collection.find({
            "student_id": student_id,
            "course_id": course_id
        }).to_list(length=None)

        # Create progress lookup
        progress_by_skill = {
            p["skill_id"]: p for p in progress_docs
        }

        # Build checklist
        checklist_items = []
        skills_mastered = 0
        skills_in_progress = 0
        skills_not_started = 0

        for skill in skills:
            skill_id = str(skill["_id"])
            progress = progress_by_skill.get(skill_id, {
                "status": "not_started",
                "mastery_level": 0.0,
                "confidence_score": 0.0,
                "practice_attempts": 0,
                "accuracy_rate": 0.0
            })

            # Count by status
            if progress["status"] == "mastered":
                skills_mastered += 1
            elif progress["status"] in ["learning", "reviewing"]:
                skills_in_progress += 1
            else:
                skills_not_started += 1

            checklist_item = {
                "skill_id": skill_id,
                "name": skill["name"],
                "description": skill["description"],
                "topic": skill["topic"],
                "difficulty": skill["difficulty"],
                "estimated_hours": skill["estimated_hours"],
                "bloom_level": skill["bloom_level"],
                "prerequisites": skill.get("prerequisites", []),
                "status": progress.get("status", "not_started"),
                "mastery_level": progress.get("mastery_level", 0.0),
                "confidence_score": progress.get("confidence_score", 0.0),
                "practice_attempts": progress.get("practice_attempts", 0),
                "accuracy_rate": progress.get("accuracy_rate", 0.0),
                "time_spent_minutes": progress.get("time_spent_minutes", 0),
                "last_practiced": progress.get("last_practiced")
            }

            checklist_items.append(checklist_item)

        # Calculate overall progress
        total_skills = len(skills)
        overall_progress = (skills_mastered / total_skills * 100) if total_skills > 0 else 0.0

        return {
            "course_id": course_id,
            "student_id": student_id,
            "skills": checklist_items,
            "overall_progress": round(overall_progress, 1),
            "skills_mastered": skills_mastered,
            "skills_in_progress": skills_in_progress,
            "skills_not_started": skills_not_started,
            "total_skills": total_skills
        }

    async def update_skill_progress(
        self,
        student_id: str,
        course_id: str,
        skill_id: str,
        is_correct: bool,
        time_spent_minutes: int
    ):
        """
        Update student progress on a skill based on practice performance
        """
        # Get or create progress document
        progress = await self.student_progress_collection.find_one({
            "student_id": student_id,
            "skill_id": skill_id
        })

        if not progress:
            # Create new progress document
            progress = {
                "student_id": student_id,
                "course_id": course_id,
                "skill_id": skill_id,
                "status": "learning",
                "mastery_level": 0.0,
                "confidence_score": 0.0,
                "practice_attempts": 0,
                "correct_count": 0,
                "accuracy_rate": 0.0,
                "time_spent_minutes": 0,
                "last_practiced": None,
                "first_practiced": datetime.utcnow(),
                "cognitive_level_achieved": None,
                "notes": None,
                "updated_at": datetime.utcnow()
            }

        # Update statistics
        practice_attempts = progress["practice_attempts"] + 1
        correct_count = progress["correct_count"] + (1 if is_correct else 0)
        accuracy_rate = (correct_count / practice_attempts) * 100
        time_spent = progress["time_spent_minutes"] + time_spent_minutes

        # Calculate mastery level (0-100)
        # Based on: accuracy, attempts, and recent performance
        # Simple formula: accuracy * (min(attempts/10, 1)) = requires both accuracy and practice
        mastery_level = accuracy_rate * min(practice_attempts / 10, 1.0)

        # Determine status
        if mastery_level >= 90 and practice_attempts >= 5:
            status = "mastered"
        elif mastery_level >= 60:
            status = "reviewing"
        elif practice_attempts > 0:
            status = "learning"
        else:
            status = "not_started"

        # Confidence score (recent performance weighted more)
        # Simplification: use accuracy as confidence
        confidence_score = accuracy_rate

        # Update document
        update_data = {
            "status": status,
            "mastery_level": round(mastery_level, 1),
            "confidence_score": round(confidence_score, 1),
            "practice_attempts": practice_attempts,
            "correct_count": correct_count,
            "accuracy_rate": round(accuracy_rate, 1),
            "time_spent_minutes": time_spent,
            "last_practiced": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        if not progress.get("_id"):
            # Insert new
            update_data["first_practiced"] = datetime.utcnow()
            await self.student_progress_collection.insert_one(update_data)
        else:
            # Update existing
            await self.student_progress_collection.update_one(
                {"_id": progress["_id"]},
                {"$set": update_data}
            )

    async def get_recommended_skills(
        self,
        student_id: str,
        course_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get recommended skills for student to work on next

        Prioritizes:
        - Skills with met prerequisites
        - Skills not yet mastered
        - Skills in student's ZPD (Zone of Proximal Development)
        """
        # Get all skills
        skills = await self.skills_collection.find({
            "course_id": course_id
        }).to_list(length=None)

        # Get student progress
        progress_docs = await self.student_progress_collection.find({
            "student_id": student_id,
            "course_id": course_id
        }).to_list(length=None)

        progress_by_skill = {p["skill_id"]: p for p in progress_docs}

        # Find recommended skills
        recommendations = []

        for skill in skills:
            skill_id = str(skill["_id"])
            progress = progress_by_skill.get(skill_id, {"status": "not_started", "mastery_level": 0.0})

            # Skip mastered skills
            if progress.get("status") == "mastered":
                continue

            # Check prerequisites
            prerequisites = skill.get("prerequisites", [])
            prerequisites_met = True

            for prereq_id in prerequisites:
                prereq_progress = progress_by_skill.get(prereq_id, {"mastery_level": 0.0})
                if prereq_progress.get("mastery_level", 0.0) < 70.0:  # Need 70% mastery of prerequisites
                    prerequisites_met = False
                    break

            if not prerequisites_met:
                continue

            # This skill is ready to work on
            recommendations.append({
                "skill_id": skill_id,
                "name": skill["name"],
                "description": skill["description"],
                "topic": skill["topic"],
                "difficulty": skill["difficulty"],
                "current_mastery": progress.get("mastery_level", 0.0),
                "estimated_hours": skill["estimated_hours"],
                "reason": "Prerequisites met" if len(prerequisites) > 0 else "Foundational skill"
            })

        # Sort by difficulty (easier first) and mastery (partially learned first)
        recommendations.sort(
            key=lambda x: (
                {"foundational": 0, "intermediate": 1, "advanced": 2}[x["difficulty"]],
                -x["current_mastery"]  # Higher mastery first (to complete in-progress)
            )
        )

        return recommendations[:limit]

    async def get_skills_by_topic(
        self,
        course_id: str,
        topic: str
    ) -> List[Dict]:
        """Get all skills for a specific topic"""
        skills = await self.skills_collection.find({
            "course_id": course_id,
            "topic": topic
        }).to_list(length=None)

        return skills

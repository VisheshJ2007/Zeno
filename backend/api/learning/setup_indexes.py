"""
Database Setup for Learning Management System
Creates indexes and prepares collections
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "zeno_db")


async def create_learning_indexes():
    """Create indexes for learning system collections"""

    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]

    logger.info("Creating indexes for Learning Management System...")

    # ========== Student Cards Collection ==========
    logger.info("Creating indexes for student_cards...")
    cards_collection = db["student_cards"]

    await cards_collection.create_index("student_id")
    await cards_collection.create_index("course_id")
    await cards_collection.create_index([("student_id", 1), ("course_id", 1)])
    await cards_collection.create_index([("student_id", 1), ("next_review", 1)])
    await cards_collection.create_index("topic")
    await cards_collection.create_index("content_ref")
    await cards_collection.create_index("skills")

    logger.info("✓ student_cards indexes created")

    # ========== Practice Sessions Collection ==========
    logger.info("Creating indexes for practice_sessions...")
    sessions_collection = db["practice_sessions"]

    await sessions_collection.create_index("student_id")
    await sessions_collection.create_index("course_id")
    await sessions_collection.create_index([("student_id", 1), ("course_id", 1)])
    await sessions_collection.create_index([("student_id", 1), ("started_at", -1)])
    await sessions_collection.create_index("status")

    logger.info("✓ practice_sessions indexes created")

    # ========== Question Bank Collection ==========
    logger.info("Creating indexes for question_bank...")
    questions_collection = db["question_bank"]

    await questions_collection.create_index("course_id")
    await questions_collection.create_index("question_id", unique=True)
    await questions_collection.create_index("topics")
    await questions_collection.create_index("skills_tested")
    await questions_collection.create_index([("course_id", 1), ("topics", 1)])
    await questions_collection.create_index("difficulty_rated")
    await questions_collection.create_index("accuracy_rate")

    logger.info("✓ question_bank indexes created")

    # ========== Skills Collection ==========
    logger.info("Creating indexes for skills...")
    skills_collection = db["skills"]

    await skills_collection.create_index("course_id")
    await skills_collection.create_index("skill_id", unique=True)
    await skills_collection.create_index([("course_id", 1), ("topic", 1)])
    await skills_collection.create_index("difficulty")
    await skills_collection.create_index("prerequisites")

    logger.info("✓ skills indexes created")

    # ========== Student Skill Progress Collection ==========
    logger.info("Creating indexes for student_skill_progress...")
    progress_collection = db["student_skill_progress"]

    await progress_collection.create_index([("student_id", 1), ("skill_id", 1)], unique=True)
    await progress_collection.create_index([("student_id", 1), ("course_id", 1)])
    await progress_collection.create_index("status")
    await progress_collection.create_index("mastery_level")
    await progress_collection.create_index([("student_id", 1), ("course_id", 1), ("status", 1)])

    logger.info("✓ student_skill_progress indexes created")

    # ========== Syllabus Alignment Collection ==========
    logger.info("Creating indexes for syllabus_alignment...")
    alignment_collection = db["syllabus_alignment"]

    await alignment_collection.create_index("course_id")
    await alignment_collection.create_index([("course_id", 1), ("student_id", 1)])
    await alignment_collection.create_index([("course_id", 1), ("analyzed_at", -1)])

    logger.info("✓ syllabus_alignment indexes created")

    logger.info("\n✅ All Learning Management System indexes created successfully!")

    client.close()


async def verify_indexes():
    """Verify that all indexes were created"""

    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]

    collections = [
        "student_cards",
        "practice_sessions",
        "question_bank",
        "skills",
        "student_skill_progress",
        "syllabus_alignment"
    ]

    logger.info("\nVerifying indexes...")

    for collection_name in collections:
        collection = db[collection_name]
        indexes = await collection.index_information()
        logger.info(f"\n{collection_name}: {len(indexes)} indexes")
        for index_name, index_info in indexes.items():
            logger.info(f"  - {index_name}: {index_info.get('key')}")

    client.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ZENO LEARNING MANAGEMENT SYSTEM - Database Setup")
    logger.info("=" * 60)

    # Create indexes
    asyncio.run(create_learning_indexes())

    # Verify indexes
    asyncio.run(verify_indexes())

    logger.info("\n" + "=" * 60)
    logger.info("Setup complete! Learning system is ready to use.")
    logger.info("=" * 60)

"""
MongoDB Vector Search Setup
Run this script once to set up MongoDB collections and indexes for RAG
"""

from pymongo import MongoClient
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_mongodb_vector_search():
    """
    Run this once to set up MongoDB Atlas vector search collections and indexes

    This script creates:
    - course_materials collection (for RAG document chunks)
    - generated_content collection (for AI-generated content)
    - semester_plans collection (for student study plans)
    - Regular indexes for efficient querying

    Note: Vector search index must be created in MongoDB Atlas UI
    """

    try:
        # Get MongoDB connection details
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        database_name = os.getenv("MONGODB_DATABASE", "zeno_db")

        print(f"Connecting to MongoDB...")
        print(f"Database: {database_name}")

        # Connect to MongoDB
        client = MongoClient(mongodb_uri)
        db = client[database_name]

        # Test connection
        client.admin.command('ping')
        print("✓ Successfully connected to MongoDB")

        # Create collections if they don't exist
        existing_collections = db.list_collection_names()
        print(f"\nExisting collections: {existing_collections}")

        collections_to_create = {
            "course_materials": "Document chunks with embeddings for RAG",
            "generated_content": "AI-generated quizzes, flashcards, etc.",
            "semester_plans": "Personalized semester study plans"
        }

        for collection_name, description in collections_to_create.items():
            if collection_name not in existing_collections:
                db.create_collection(collection_name)
                print(f"✓ Created collection: {collection_name} ({description})")
            else:
                print(f"  Collection already exists: {collection_name}")

        # Create indexes for course_materials collection
        print("\nCreating indexes for course_materials...")
        course_materials = db.course_materials

        # Index on course_id for filtering
        course_materials.create_index([("course_id", 1)], name="course_id_idx")
        print("✓ Created index: course_id_idx")

        # Index on doc_type for filtering by document type
        course_materials.create_index([("doc_type", 1)], name="doc_type_idx")
        print("✓ Created index: doc_type_idx")

        # Compound index for course_id + doc_type queries
        course_materials.create_index(
            [("course_id", 1), ("doc_type", 1)],
            name="course_doc_type_idx"
        )
        print("✓ Created index: course_doc_type_idx")

        # Index on metadata fields for filtering
        course_materials.create_index([("metadata.topic", 1)], name="topic_idx")
        print("✓ Created index: topic_idx")

        course_materials.create_index([("metadata.difficulty", 1)], name="difficulty_idx")
        print("✓ Created index: difficulty_idx")

        course_materials.create_index([("metadata.exam_relevant", 1)], name="exam_relevant_idx")
        print("✓ Created index: exam_relevant_idx")

        # Index on created_at for sorting
        course_materials.create_index([("created_at", -1)], name="created_at_idx")
        print("✓ Created index: created_at_idx")

        # Create indexes for generated_content collection
        print("\nCreating indexes for generated_content...")
        generated_content = db.generated_content

        generated_content.create_index([("course_id", 1)], name="course_id_idx")
        generated_content.create_index([("content_type", 1)], name="content_type_idx")
        generated_content.create_index(
            [("course_id", 1), ("content_type", 1)],
            name="course_content_type_idx"
        )
        generated_content.create_index([("created_at", -1)], name="created_at_idx")
        print("✓ Created indexes for generated_content")

        # Create indexes for semester_plans collection
        print("\nCreating indexes for semester_plans...")
        semester_plans = db.semester_plans

        semester_plans.create_index([("student_id", 1)], name="student_id_idx")
        semester_plans.create_index([("course_id", 1)], name="course_id_idx")
        semester_plans.create_index(
            [("student_id", 1), ("course_id", 1)],
            name="student_course_idx"
        )
        semester_plans.create_index([("created_at", -1)], name="created_at_idx")
        print("✓ Created indexes for semester_plans")

        # Print vector search index instructions
        print("\n" + "="*70)
        print("IMPORTANT: Vector Search Index Setup Required")
        print("="*70)
        print("\nYou must manually create the vector search index in MongoDB Atlas UI:")
        print("\n1. Go to your MongoDB Atlas cluster")
        print("2. Navigate to 'Search' tab")
        print("3. Click 'Create Search Index'")
        print("4. Choose 'JSON Editor'")
        print("5. Paste the following configuration:\n")

        vector_index_config = """{
  "fields": [
    {
      "type": "vector",
      "path": "content_vector",
      "numDimensions": 1536,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "course_id"
    },
    {
      "type": "filter",
      "path": "doc_type"
    },
    {
      "type": "filter",
      "path": "metadata.topic"
    },
    {
      "type": "filter",
      "path": "metadata.difficulty"
    },
    {
      "type": "filter",
      "path": "metadata.exam_relevant"
    }
  ]
}"""

        print(vector_index_config)
        print("\n6. Index name: 'course_materials_vector_index'")
        print("7. Database: '" + database_name + "'")
        print("8. Collection: 'course_materials'")
        print("9. Click 'Create Search Index'")
        print("\n" + "="*70)

        print("\n✅ MongoDB setup completed successfully!")
        print("\nNext steps:")
        print("1. Create the vector search index in MongoDB Atlas UI (see instructions above)")
        print("2. Configure Azure OpenAI credentials in .env file")
        print("3. Install required Python packages: openai, langchain, nemoguardrails")
        print("4. Test the RAG health endpoint: GET /api/rag/health")

        return True

    except Exception as e:
        print(f"\n❌ Error during MongoDB setup: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'client' in locals():
            client.close()
            print("\nMongoDB connection closed")


def drop_rag_collections():
    """
    Drop RAG collections (USE WITH CAUTION!)
    This will delete all course materials, generated content, and semester plans
    """

    try:
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        database_name = os.getenv("MONGODB_DATABASE", "zeno_db")

        client = MongoClient(mongodb_uri)
        db = client[database_name]

        collections_to_drop = ["course_materials", "generated_content", "semester_plans"]

        print("⚠️  WARNING: This will delete all RAG-related data!")
        response = input("Are you sure you want to continue? (yes/no): ")

        if response.lower() == "yes":
            for collection in collections_to_drop:
                if collection in db.list_collection_names():
                    db.drop_collection(collection)
                    print(f"✓ Dropped collection: {collection}")
            print("\n✅ All RAG collections dropped")
        else:
            print("Operation cancelled")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MongoDB Vector Search Setup for Zeno RAG")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all RAG collections (USE WITH CAUTION!)"
    )

    args = parser.parse_args()

    if args.drop:
        drop_rag_collections()
    else:
        setup_mongodb_vector_search()

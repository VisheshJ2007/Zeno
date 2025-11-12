"""
Core RAG Engine for Zeno Tutoring Platform
Handles embedding generation, retrieval, and RAG-based generation
"""

from typing import List, Dict, Optional, Any
from openai import AzureOpenAI
from pymongo import MongoClient
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class ZenoRAGEngine:
    """
    Core RAG engine for Zeno tutoring platform
    Handles embedding generation, retrieval, and RAG-based generation
    """

    def __init__(self):
        """Initialize RAG engine with Azure OpenAI and MongoDB clients"""

        # Azure OpenAI Client
        try:
            self.azure_client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            logger.info("Azure OpenAI client initialized")
        except Exception as e:
            logger.warning(f"Azure OpenAI client initialization failed: {e}")
            self.azure_client = None

        # MongoDB Client
        try:
            mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            self.mongo_client = MongoClient(mongodb_uri)
            database_name = os.getenv("MONGODB_DATABASE", "zeno_db")
            self.db = self.mongo_client[database_name]

            # Collections
            self.course_materials = self.db["course_materials"]
            self.generated_content = self.db["generated_content"]
            self.semester_plans = self.db["semester_plans"]

            logger.info(f"MongoDB client initialized (database: {database_name})")
        except Exception as e:
            logger.error(f"MongoDB client initialization failed: {e}")
            raise

        # Model configurations
        self.embedding_model = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
        self.chat_model = os.getenv("AZURE_CHAT_DEPLOYMENT", "gpt-4")

        # Vector search index name
        self.vector_index_name = "course_materials_vector_index"

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using Azure OpenAI

        Args:
            text: Text to embed

        Returns:
            1536-dimensional embedding vector

        Raises:
            Exception if Azure OpenAI is not configured
        """
        if not self.azure_client:
            raise Exception("Azure OpenAI client not initialized. Check your environment variables.")

        try:
            response = self.azure_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def retrieve_relevant_chunks(
        self,
        query: str,
        course_id: str,
        k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve top-k most relevant chunks using MongoDB Atlas Vector Search

        Args:
            query: Search query text
            course_id: Course identifier
            k: Number of chunks to retrieve
            filters: Additional MongoDB filters (doc_type, metadata fields, etc.)

        Returns:
            List of relevant chunks with content and metadata
        """
        try:
            # Generate query embedding
            query_vector = await self.generate_embedding(query)

            # Build filter condition
            filter_condition = {"course_id": course_id}
            if filters:
                filter_condition.update(filters)

            # MongoDB aggregation pipeline for vector search
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.vector_index_name,
                        "path": "content_vector",
                        "queryVector": query_vector,
                        "numCandidates": k * 10,  # Oversample for better results
                        "limit": k,
                        "filter": filter_condition
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "content": 1,
                        "metadata": 1,
                        "doc_type": 1,
                        "source_file": 1,
                        "chunk_index": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            results = list(self.course_materials.aggregate(pipeline))
            logger.info(f"Retrieved {len(results)} chunks for query: '{query[:50]}...'")
            return results

        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []

    async def generate_with_rag(
        self,
        query: str,
        course_id: str,
        system_prompt: str,
        k: int = 5,
        filters: Optional[Dict] = None,
        temperature: float = 0.3,
        max_tokens: int = 1500
    ) -> Dict:
        """
        Generate response using Retrieval-Augmented Generation

        Args:
            query: User query
            course_id: Course identifier
            system_prompt: System prompt for generation
            k: Number of chunks to retrieve
            filters: Optional filters for retrieval
            temperature: Generation temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            {
                "response": str,
                "sources": List[Dict],
                "usage": Dict
            }
        """
        if not self.azure_client:
            return {
                "response": "Azure OpenAI is not configured. Please check your environment variables.",
                "sources": [],
                "usage": {}
            }

        try:
            # 1. Retrieve relevant chunks
            relevant_chunks = await self.retrieve_relevant_chunks(
                query, course_id, k=k, filters=filters
            )

            if not relevant_chunks:
                return {
                    "response": "I couldn't find relevant information in the course materials to answer this question. Could you rephrase or provide more context?",
                    "sources": [],
                    "usage": {}
                }

            # 2. Build context from retrieved chunks
            context_parts = []
            for i, chunk in enumerate(relevant_chunks, 1):
                context_parts.append(
                    f"[Source {i}: {chunk['source_file']}, "
                    f"Type: {chunk['doc_type']}, "
                    f"Relevance: {chunk['score']:.3f}]\n"
                    f"{chunk['content']}\n"
                )

            context = "\n".join(context_parts)

            # 3. Create RAG prompt
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
Based on the following course materials, please answer the question.

COURSE MATERIALS:
{context}

QUESTION: {query}

INSTRUCTIONS:
- Base your answer ONLY on the provided course materials
- If the information isn't in the materials, say so explicitly
- Reference specific sources when making claims
- Maintain an educational, supportive tone
- Guide the student to understanding rather than giving direct answers
"""}
            ]

            # 4. Generate response
            response = self.azure_client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # 5. Prepare output
            return {
                "response": response.choices[0].message.content,
                "sources": [
                    {
                        "source_file": chunk["source_file"],
                        "doc_type": chunk["doc_type"],
                        "relevance_score": chunk["score"],
                        "metadata": chunk.get("metadata", {}),
                        "chunk_id": str(chunk["_id"])
                    }
                    for chunk in relevant_chunks
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            logger.error(f"Error in RAG generation: {e}")
            return {
                "response": f"An error occurred during generation: {str(e)}",
                "sources": [],
                "usage": {}
            }

    async def multi_query_retrieval(
        self,
        queries: List[str],
        course_id: str,
        k_per_query: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve chunks for multiple queries (for comprehensive content generation)
        Used for semester plans, practice exams, etc.

        Args:
            queries: List of query strings
            course_id: Course identifier
            k_per_query: Number of chunks to retrieve per query
            filters: Optional filters

        Returns:
            Combined list of unique chunks, sorted by relevance
        """
        all_chunks = []
        seen_chunk_ids = set()

        for query in queries:
            chunks = await self.retrieve_relevant_chunks(
                query, course_id, k=k_per_query, filters=filters
            )

            for chunk in chunks:
                chunk_id = str(chunk["_id"])
                if chunk_id not in seen_chunk_ids:
                    all_chunks.append(chunk)
                    seen_chunk_ids.add(chunk_id)

        # Sort by score descending
        all_chunks.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"Multi-query retrieval: {len(queries)} queries → {len(all_chunks)} unique chunks")

        return all_chunks

    async def generate_with_multi_query_rag(
        self,
        queries: List[str],
        course_id: str,
        system_prompt: str,
        user_prompt_template: str,
        k_per_query: int = 5,
        filters: Optional[Dict] = None,
        temperature: float = 0.5,
        max_tokens: int = 3000
    ) -> Dict:
        """
        Generate content using multi-query retrieval

        Args:
            queries: List of query strings
            course_id: Course identifier
            system_prompt: System prompt
            user_prompt_template: User prompt template (use {context} placeholder)
            k_per_query: Chunks per query
            filters: Optional filters
            temperature: Generation temperature
            max_tokens: Maximum tokens

        Returns:
            Generation result with response, sources, and usage
        """
        if not self.azure_client:
            return {
                "response": "Azure OpenAI is not configured.",
                "sources": [],
                "usage": {}
            }

        try:
            # Multi-query retrieval
            all_chunks = await self.multi_query_retrieval(
                queries, course_id, k_per_query, filters
            )

            if not all_chunks:
                return {
                    "response": "No relevant course materials found.",
                    "sources": [],
                    "usage": {}
                }

            # Build context
            context = "\n\n".join([
                f"[{chunk['source_file']} - Score: {chunk['score']:.3f}]\n{chunk['content']}"
                for chunk in all_chunks[:20]  # Top 20 chunks
            ])

            # Create messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_template.format(context=context)}
            ]

            # Generate
            response = self.azure_client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return {
                "response": response.choices[0].message.content,
                "sources": [
                    {
                        "source_file": chunk["source_file"],
                        "relevance": chunk["score"]
                    }
                    for chunk in all_chunks[:10]
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            logger.error(f"Error in multi-query RAG: {e}")
            return {
                "response": f"Error: {str(e)}",
                "sources": [],
                "usage": {}
            }

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of RAG system components

        Returns:
            Health status dictionary
        """
        health = {
            "status": "unknown",
            "components": {}
        }

        # Check MongoDB
        try:
            self.mongo_client.admin.command('ping')
            health["components"]["mongodb"] = "healthy"
        except Exception as e:
            health["components"]["mongodb"] = f"unhealthy: {str(e)}"

        # Check Azure OpenAI
        if self.azure_client:
            try:
                # Try to generate a simple embedding
                test_response = self.azure_client.embeddings.create(
                    model=self.embedding_model,
                    input="test"
                )
                embedding_dim = len(test_response.data[0].embedding)
                health["components"]["azure_openai"] = f"healthy (embedding dim: {embedding_dim})"
            except Exception as e:
                health["components"]["azure_openai"] = f"unhealthy: {str(e)}"
        else:
            health["components"]["azure_openai"] = "not configured"

        # Check vector index
        try:
            indexes = list(self.course_materials.list_search_indexes())
            vector_index_exists = any(
                idx.get("name") == self.vector_index_name
                for idx in indexes
            )
            health["components"]["vector_index"] = "exists" if vector_index_exists else "not found"
        except Exception as e:
            health["components"]["vector_index"] = f"error: {str(e)}"

        # Overall status
        all_healthy = all(
            "healthy" in str(status) or "exists" in str(status)
            for status in health["components"].values()
        )
        health["status"] = "healthy" if all_healthy else "degraded"

        return health


# Global instance
rag_engine = ZenoRAGEngine()

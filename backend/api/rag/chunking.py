"""
Intelligent Document Chunking System
Provides document-type-specific chunking strategies for optimal RAG performance
"""

from typing import List, Dict, Optional
import re
from dataclasses import dataclass


@dataclass
class ChunkConfig:
    """Configuration for document chunking"""
    chunk_size: int
    chunk_overlap: int
    separators: List[str]


class RecursiveCharacterTextSplitter:
    """
    Simple implementation of recursive character text splitting
    Similar to LangChain's RecursiveCharacterTextSplitter
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
        length_function=len
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
        self.length_function = length_function

    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks using recursive character splitting

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        return self._split_text_recursive(text, self.separators)

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using separators"""

        final_chunks = []

        # Get appropriate separator
        separator = separators[-1] if separators else ""
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        # Split by separator
        splits = text.split(separator) if separator else [text]

        # Merge splits into chunks
        good_splits = []
        for split in splits:
            if self.length_function(split) < self.chunk_size:
                good_splits.append(split)
            else:
                # Split is too large, need to split further
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []

                if new_separators:
                    # Recursively split with remaining separators
                    other_chunks = self._split_text_recursive(split, new_separators)
                    final_chunks.extend(other_chunks)
                else:
                    # No more separators, force split
                    final_chunks.append(split)

        # Merge remaining splits
        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)

        return final_chunks

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """Merge splits into chunks of appropriate size"""

        chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            split_len = self.length_function(split)

            # Check if adding this split would exceed chunk size
            if current_length + split_len + len(separator) > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = separator.join(current_chunk)
                if chunk_text:
                    chunks.append(chunk_text)

                # Start new chunk with overlap
                # Keep last few splits for overlap
                overlap_splits = []
                overlap_length = 0
                for prev_split in reversed(current_chunk):
                    prev_len = self.length_function(prev_split)
                    if overlap_length + prev_len <= self.chunk_overlap:
                        overlap_splits.insert(0, prev_split)
                        overlap_length += prev_len + len(separator)
                    else:
                        break

                current_chunk = overlap_splits
                current_length = overlap_length

            current_chunk.append(split)
            current_length += split_len + len(separator)

        # Add final chunk
        if current_chunk:
            chunk_text = separator.join(current_chunk)
            if chunk_text:
                chunks.append(chunk_text)

        return chunks


class IntelligentChunker:
    """
    Intelligent document chunking with document-type-specific strategies
    Optimized for educational content and RAG
    """

    # Chunking configurations for different document types
    CHUNK_CONFIGS = {
        "syllabus": ChunkConfig(
            chunk_size=400,
            chunk_overlap=30,
            separators=["\n\n## ", "\n\n### ", "\n\n", "\n", ". ", " ", ""]
        ),
        "lecture_notes": ChunkConfig(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n## ", "\n\n### ", "\n\n", "\n", ". ", " ", ""]
        ),
        "textbook": ChunkConfig(
            chunk_size=600,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " ", ""]
        ),
        "exam": ChunkConfig(
            chunk_size=300,
            chunk_overlap=0,  # Don't overlap exam questions
            separators=["\n\n", "\n"]
        ),
        "default": ChunkConfig(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    }

    def __init__(self):
        """Initialize chunker with splitters for each document type"""
        self.splitters = {}

        # Create splitters for each document type
        for doc_type, config in self.CHUNK_CONFIGS.items():
            self.splitters[doc_type] = RecursiveCharacterTextSplitter(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                separators=config.separators,
                length_function=len
            )

    def chunk_document(
        self,
        text: str,
        doc_type: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Chunk document with type-specific strategy

        Args:
            text: Document text to chunk
            doc_type: Document type (syllabus, lecture_notes, textbook, exam)
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with:
            {
                "text": str,
                "metadata": Dict (includes extracted info + provided metadata)
            }
        """

        # Get appropriate splitter
        splitter = self.splitters.get(doc_type, self.splitters["default"])

        # Split text into chunks
        raw_chunks = splitter.split_text(text)

        # Enhance chunks with metadata
        enhanced_chunks = []
        for i, chunk_text in enumerate(raw_chunks):
            chunk_metadata = {
                **(metadata or {}),
                "chunk_index": i,
                "total_chunks": len(raw_chunks)
            }

            # Extract additional metadata from chunk content
            chunk_metadata.update(self._extract_metadata(chunk_text, doc_type))

            enhanced_chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })

        return enhanced_chunks

    def _extract_metadata(self, text: str, doc_type: str) -> Dict:
        """
        Extract metadata from chunk text

        Args:
            text: Chunk text
            doc_type: Document type

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}

        # Extract topic from headers (# Topic, ## Topic, ### Topic)
        header_match = re.search(r'^#+\s+(.+)$', text, re.MULTILINE)
        if header_match:
            metadata["topic"] = header_match.group(1).strip()

        # Estimate difficulty based on text complexity
        avg_word_length = self._calculate_avg_word_length(text)
        if avg_word_length < 5:
            metadata["difficulty"] = "easy"
        elif avg_word_length < 7:
            metadata["difficulty"] = "medium"
        else:
            metadata["difficulty"] = "hard"

        # Check for exam-relevant keywords
        exam_keywords = [
            "exam", "test", "quiz", "assessment", "evaluate",
            "important", "key concept", "remember", "memorize",
            "critical", "essential", "fundamental", "must know"
        ]
        text_lower = text.lower()
        metadata["exam_relevant"] = any(
            keyword in text_lower for keyword in exam_keywords
        )

        # Extract page numbers if present
        page_match = re.search(r'page\s+(\d+)', text, re.IGNORECASE)
        if page_match:
            metadata["page_number"] = int(page_match.group(1))

        # Extract section numbers (e.g., "1.2", "3.4.1")
        section_match = re.search(r'^\s*(\d+(?:\.\d+)*)\s+', text, re.MULTILINE)
        if section_match:
            metadata["section"] = section_match.group(1)

        # Check for mathematical content
        has_equations = bool(
            re.search(r'[\=\+\-\*\/\(\)\^\$]|\d+\s*[a-z]\s*[\+\-\=]', text)
        )
        metadata["has_math"] = has_equations

        # Check for code blocks
        has_code = bool(
            re.search(r'```|`[^`]+`|^\s{4,}[a-zA-Z]', text, re.MULTILINE)
        )
        metadata["has_code"] = has_code

        return metadata

    def _calculate_avg_word_length(self, text: str) -> float:
        """Calculate average word length in text"""
        words = re.findall(r'\b\w+\b', text)
        if not words:
            return 0.0
        return sum(len(word) for word in words) / len(words)

    def chunk_with_overlap_context(
        self,
        text: str,
        doc_type: str,
        metadata: Optional[Dict] = None,
        context_size: int = 100
    ) -> List[Dict]:
        """
        Chunk document and include surrounding context in metadata

        Args:
            text: Document text
            doc_type: Document type
            metadata: Optional metadata
            context_size: Number of characters of context to include

        Returns:
            List of chunk dictionaries with context
        """

        chunks = self.chunk_document(text, doc_type, metadata)

        # Add surrounding context to each chunk
        for i, chunk in enumerate(chunks):
            # Add previous context
            if i > 0:
                prev_text = chunks[i - 1]["text"]
                chunk["metadata"]["prev_context"] = prev_text[-context_size:]

            # Add next context
            if i < len(chunks) - 1:
                next_text = chunks[i + 1]["text"]
                chunk["metadata"]["next_context"] = next_text[:context_size]

        return chunks


# Global instance
chunker = IntelligentChunker()


# Utility functions for easy access
def chunk_text(
    text: str,
    doc_type: str = "default",
    metadata: Optional[Dict] = None
) -> List[Dict]:
    """
    Convenience function to chunk text

    Args:
        text: Text to chunk
        doc_type: Document type
        metadata: Optional metadata

    Returns:
        List of chunks with metadata
    """
    return chunker.chunk_document(text, doc_type, metadata)


def get_chunk_config(doc_type: str) -> ChunkConfig:
    """
    Get chunk configuration for document type

    Args:
        doc_type: Document type

    Returns:
        ChunkConfig for the document type
    """
    return IntelligentChunker.CHUNK_CONFIGS.get(
        doc_type,
        IntelligentChunker.CHUNK_CONFIGS["default"]
    )

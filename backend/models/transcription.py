"""
Pydantic Models for OCR Transcription API
Defines request/response models and database schema
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, validator


# ============================================================================
# Enums and Type Definitions
# ============================================================================

DocumentType = Literal[
    "lecture_notes",
    "syllabus",
    "textbook",
    "problem_set",
    "handwritten_notes",
    "exam",
    "homework",
    "research_paper",
    "unknown"
]

AcademicSubject = Literal[
    "mathematics",
    "calculus",
    "algebra",
    "geometry",
    "statistics",
    "physics",
    "chemistry",
    "biology",
    "computer_science",
    "engineering",
    "english",
    "history",
    "economics",
    "unknown"
]

FileType = Literal[
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "application/pdf"
]

ProcessingStatus = Literal["processing", "processed", "failed"]


# ============================================================================
# Nested Models (Sub-documents)
# ============================================================================

class FileMetadata(BaseModel):
    """File metadata model"""
    original_filename: str = Field(
        ...,
        description="Original filename of the uploaded file"
    )
    file_size_bytes: int = Field(
        ...,
        gt=0,
        description="File size in bytes"
    )
    file_type: FileType = Field(
        ...,
        description="MIME type of the file"
    )
    upload_timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp when file was uploaded"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "original_filename": "lecture_notes.jpg",
                "file_size_bytes": 2048576,
                "file_type": "image/jpeg",
                "upload_timestamp": "2025-11-07T10:30:00Z"
            }
        }


class OCRData(BaseModel):
    """OCR processing data model"""
    raw_text: str = Field(
        ...,
        description="Raw text output from Tesseract.js"
    )
    cleaned_text: str = Field(
        ...,
        description="Cleaned and corrected text"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="OCR confidence score (0-100)"
    )
    processing_time_ms: int = Field(
        ...,
        ge=0,
        description="Time taken to process OCR in milliseconds"
    )
    tesseract_version: Optional[str] = Field(
        default=None,
        description="Tesseract version used for OCR"
    )
    language: str = Field(
        default="eng",
        description="Language code used for OCR"
    )

    @validator('cleaned_text')
    def cleaned_text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Cleaned text cannot be empty')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "raw_text": "Thls is sorne OCR text...",
                "cleaned_text": "This is some OCR text...",
                "confidence": 85.5,
                "processing_time_ms": 3200,
                "tesseract_version": "4.0.0",
                "language": "eng"
            }
        }


class DocumentSection(BaseModel):
    """Document section model"""
    title: str = Field(
        ...,
        description="Section title or heading"
    )
    content: str = Field(
        ...,
        description="Section content"
    )
    line_start: Optional[int] = Field(
        default=None,
        description="Starting line number"
    )
    line_end: Optional[int] = Field(
        default=None,
        description="Ending line number"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Introduction",
                "content": "This is the introduction section...",
                "line_start": 0,
                "line_end": 10
            }
        }


class StructuredContent(BaseModel):
    """Structured document content model"""
    document_type: DocumentType = Field(
        ...,
        description="Detected document type"
    )
    sections: List[DocumentSection] = Field(
        default_factory=list,
        description="Document sections"
    )
    paragraphs: List[str] = Field(
        default_factory=list,
        description="Document paragraphs"
    )
    detected_subject: Optional[AcademicSubject] = Field(
        default=None,
        description="Detected academic subject"
    )
    word_count: int = Field(
        ...,
        ge=0,
        description="Total word count"
    )
    has_formulas: bool = Field(
        default=False,
        description="Whether document contains mathematical formulas"
    )
    has_tables: bool = Field(
        default=False,
        description="Whether document contains tables"
    )
    has_lists: bool = Field(
        default=False,
        description="Whether document contains lists"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_type": "lecture_notes",
                "sections": [
                    {
                        "title": "Chapter 1: Introduction",
                        "content": "This chapter introduces...",
                        "line_start": 0,
                        "line_end": 20
                    }
                ],
                "paragraphs": ["First paragraph...", "Second paragraph..."],
                "detected_subject": "calculus",
                "word_count": 1500,
                "has_formulas": True,
                "has_tables": False,
                "has_lists": True
            }
        }


# ============================================================================
# API Request Models
# ============================================================================

class TranscriptionRequest(BaseModel):
    """Request model for OCR transcription"""
    filename: str = Field(
        ...,
        description="Filename for this transcription"
    )
    file_metadata: FileMetadata = Field(
        ...,
        description="File metadata"
    )
    ocr_data: OCRData = Field(
        ...,
        description="OCR processing data"
    )
    structured_content: StructuredContent = Field(
        ...,
        description="Structured document content"
    )
    user_id: str = Field(
        ...,
        description="User ID who submitted the transcription"
    )

    @validator('user_id')
    def user_id_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "lecture_notes.jpg",
                "file_metadata": {
                    "original_filename": "lecture_notes.jpg",
                    "file_size_bytes": 2048576,
                    "file_type": "image/jpeg",
                    "upload_timestamp": "2025-11-07T10:30:00Z"
                },
                "ocr_data": {
                    "raw_text": "Original text...",
                    "cleaned_text": "Cleaned text...",
                    "confidence": 85.5,
                    "processing_time_ms": 3200,
                    "language": "eng"
                },
                "structured_content": {
                    "document_type": "lecture_notes",
                    "sections": [],
                    "paragraphs": [],
                    "detected_subject": "calculus",
                    "word_count": 1500,
                    "has_formulas": True,
                    "has_tables": False,
                    "has_lists": True
                },
                "user_id": "user123"
            }
        }


# ============================================================================
# API Response Models
# ============================================================================

class TranscriptionResponse(BaseModel):
    """Response model for successful transcription"""
    success: bool = Field(
        default=True,
        description="Whether the operation was successful"
    )
    transcription_id: str = Field(
        ...,
        description="Unique transcription ID (UUID)"
    )
    message: Optional[str] = Field(
        default="Transcription processed successfully",
        description="Success message"
    )
    created_at: str = Field(
        ...,
        description="ISO 8601 timestamp when transcription was created"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "transcription_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Transcription processed successfully",
                "created_at": "2025-11-07T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors"""
    success: bool = Field(
        default=False,
        description="Whether the operation was successful"
    )
    error: str = Field(
        ...,
        description="Error message"
    )
    detail: Optional[str] = Field(
        default=None,
        description="Detailed error information"
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp when error occurred"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Invalid request data",
                "detail": "Field 'user_id' is required",
                "timestamp": "2025-11-07T10:30:00Z"
            }
        }


# ============================================================================
# MongoDB Document Models
# ============================================================================

class OCRMetadata(BaseModel):
    """OCR processing metadata"""
    confidence_score: float = Field(
        ..., ge=0.0, le=100.0
    )
    processing_time_ms: int
    tesseract_version: Optional[str] = None
    language: str = "eng"


class ContentData(BaseModel):
    """Content data for MongoDB"""
    raw_text: str
    cleaned_text: str
    summary: Optional[str] = Field(
        default=None,
        description="Short 1-2 sentence summary generated by LLM"
    )
    key_topics: List[str] = Field(
        default_factory=list,
        description="List of concise key topic phrases generated by LLM"
    )
    structured_content: StructuredContent


class MongoDBDocument(BaseModel):
    """Complete MongoDB document schema"""
    transcription_id: str = Field(
        ...,
        description="Unique transcription ID (UUID)"
    )
    user_id: str = Field(
        ...,
        description="User ID who submitted the transcription"
    )
    file_info: FileMetadata = Field(
        ...,
        description="File information"
    )
    content: ContentData = Field(
        ...,
        description="OCR content data"
    )
    ocr_metadata: OCRMetadata = Field(
        ...,
        description="OCR processing metadata"
    )
    status: ProcessingStatus = Field(
        default="processed",
        description="Processing status"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if status is 'failed'"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    searchable_text: str = Field(
        ...,
        description="Cleaned text for full-text search"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "transcription_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user123",
                "file_info": {
                    "original_filename": "lecture_notes.jpg",
                    "file_size_bytes": 2048576,
                    "file_type": "image/jpeg",
                    "upload_timestamp": "2025-11-07T10:30:00Z"
                },
                "content": {
                    "raw_text": "Original text...",
                    "cleaned_text": "Cleaned text...",
                    "summary": "A short summary of the document.",
                    "key_topics": ["topic A", "topic B"],
                    "structured_content": {
                        "document_type": "lecture_notes",
                        "sections": [],
                        "paragraphs": [],
                        "detected_subject": "calculus",
                        "word_count": 1500,
                        "has_formulas": True,
                        "has_tables": False,
                        "has_lists": True
                    }
                },
                "ocr_metadata": {
                    "confidence_score": 85.5,
                    "processing_time_ms": 3200,
                    "tesseract_version": "4.0.0",
                    "language": "eng"
                },
                "status": "processed",
                "error_message": None,
                "created_at": "2025-11-07T10:30:00",
                "updated_at": "2025-11-07T10:30:00",
                "searchable_text": "Cleaned text for searching..."
            }
        }


# ============================================================================
# Utility Functions
# ============================================================================

def create_mongodb_document(
    transcription_id: str,
    request: TranscriptionRequest
) -> dict:
    """
    Create MongoDB document from transcription request

    Args:
        transcription_id: UUID for this transcription
        request: TranscriptionRequest object

    Returns:
        Dictionary ready for MongoDB insertion
    """
    now = datetime.utcnow()

    doc = MongoDBDocument(
        transcription_id=transcription_id,
        user_id=request.user_id,
        file_info=request.file_metadata,
        content=ContentData(
            raw_text=request.ocr_data.raw_text,
            cleaned_text=request.ocr_data.cleaned_text,
            structured_content=request.structured_content
        ),
        ocr_metadata=OCRMetadata(
            confidence_score=request.ocr_data.confidence,
            processing_time_ms=request.ocr_data.processing_time_ms,
            tesseract_version=request.ocr_data.tesseract_version,
            language=request.ocr_data.language
        ),
        status="processed",
        error_message=None,
        created_at=now,
        updated_at=now,
        searchable_text=request.ocr_data.cleaned_text
    )

    # Convert to dict for MongoDB insertion
    doc_dict = doc.model_dump()

    # Convert datetime objects to ISO strings for MongoDB
    doc_dict['created_at'] = doc_dict['created_at'].isoformat()
    doc_dict['updated_at'] = doc_dict['updated_at'].isoformat()

    return doc_dict

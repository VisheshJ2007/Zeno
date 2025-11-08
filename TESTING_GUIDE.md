# Zeno Platform - Testing Guide

Comprehensive testing documentation for OCR, RAG, and Learning Management systems.

---

## 📋 Table of Contents

1. [Testing Overview](#testing-overview)
2. [OCR System Tests](#ocr-system-tests)
3. [RAG System Tests](#rag-system-tests)
4. [Learning System Tests](#learning-system-tests)
5. [Integration Tests](#integration-tests)
6. [Performance Tests](#performance-tests)
7. [Test Data](#test-data)

---

## 1. Testing Overview

### Test Categories

| Category | Description | Tools |
|----------|-------------|-------|
| **Unit Tests** | Individual functions | pytest |
| **Integration Tests** | System interactions | pytest, curl |
| **API Tests** | Endpoint validation | curl, Postman |
| **Frontend Tests** | Component testing | Jest, React Testing Library |
| **Performance Tests** | Load and speed | pytest-benchmark |

### Prerequisites for Testing

```bash
# Backend
cd backend
source .venv/bin/activate
pip install pytest pytest-asyncio httpx

# Frontend
cd frontend
npm install --save-dev jest @testing-library/react
```

---

## 2. OCR System Tests

### Test 2.1: Upload and Transcribe Document

**Endpoint**: `POST /api/ocr/transcribe`

```bash
curl -X POST http://localhost:8000/api/ocr/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_001",
    "file_info": {
      "original_filename": "lecture1.pdf",
      "file_size_bytes": 102400,
      "file_type": "application/pdf",
      "upload_timestamp": "2024-01-15T10:00:00Z"
    },
    "content": {
      "raw_text": "Introduction to Algorithms. Chapter 1: Fundamentals.",
      "cleaned_text": "Introduction to Algorithms. Chapter 1: Fundamentals.",
      "structured_content": {
        "document_type": "lecture_notes",
        "sections": ["Introduction", "Fundamentals"],
        "paragraphs": ["Introduction to Algorithms.", "Chapter 1: Fundamentals."],
        "detected_subject": "computer_science",
        "word_count": 7,
        "has_formulas": false,
        "has_tables": false,
        "has_lists": false
      }
    },
    "ocr_metadata": {
      "confidence_score": 95.5,
      "processing_time_ms": 1234,
      "tesseract_version": "5.0.4",
      "language": "eng"
    },
    "status": "processed"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "transcription_id": "uuid-here",
  "message": "Transcription created successfully",
  "created_at": "2024-01-15T10:00:01Z"
}
```

**Test Validation**:
- ✅ Status code: 200
- ✅ Returns transcription_id
- ✅ Created timestamp present

### Test 2.2: Retrieve Transcription

**Endpoint**: `GET /api/ocr/transcription/{id}`

```bash
TRANSCRIPTION_ID="your-transcription-id"
curl "http://localhost:8000/api/ocr/transcription/${TRANSCRIPTION_ID}"
```

**Expected Response**: Full transcription object

### Test 2.3: Search Transcriptions

**Endpoint**: `GET /api/ocr/search`

```bash
curl "http://localhost:8000/api/ocr/search?q=algorithms"
```

**Expected**: Array of matching transcriptions

### Test 2.4: Get User Statistics

**Endpoint**: `GET /api/ocr/user/{user_id}/statistics`

```bash
curl "http://localhost:8000/api/ocr/user/test_user_001/statistics"
```

**Expected Response**:
```json
{
  "total_transcriptions": 5,
  "total_file_size_bytes": 512000,
  "average_confidence": 92.3,
  "document_types": {"lecture_notes": 3, "textbook": 2}
}
```

---

## 3. RAG System Tests

### Test 3.1: Health Check

**Endpoint**: `GET /api/rag/health`

```bash
curl http://localhost:8000/api/rag/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "components": {
    "mongodb": "healthy",
    "azure_openai": "healthy (embedding dim: 1536)",
    "vector_index": "exists"
  }
}
```

**Test Validation**:
- ✅ All components show "healthy"
- ✅ Vector index exists
- ✅ Embedding dimension is 1536

### Test 3.2: Process Document for RAG

**Endpoint**: `POST /api/rag/process-document`

```bash
curl -X POST http://localhost:8000/api/rag/process-document \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CS101_Fall_2024",
    "doc_type": "lecture_notes",
    "source_file": "lecture1.pdf",
    "ocr_text": "Introduction to Algorithms. Big O notation is a mathematical notation that describes the limiting behavior of a function. Time complexity analysis helps us understand algorithm efficiency. Sorting algorithms like quicksort and mergesort are fundamental.",
    "metadata": {
      "topic": "Introduction to Algorithms",
      "week": 1,
      "difficulty": "foundational"
    }
  }'
```

**Expected Response**:
```json
{
  "status": "processing",
  "message": "Document lecture1.pdf is being processed for RAG",
  "course_id": "CS101_Fall_2024",
  "doc_type": "lecture_notes"
}
```

**Verify in MongoDB**:
```javascript
// Check documents were created
db.course_materials.find({
  course_id: "CS101_Fall_2024",
  source_file: "lecture1.pdf"
}).count()

// Should return: 3-5 chunks
```

### Test 3.3: Generate Quiz

**Endpoint**: `POST /api/rag/generate-quiz`

```bash
# Wait 5-10 seconds after processing document
curl -X POST http://localhost:8000/api/rag/generate-quiz \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CS101_Fall_2024",
    "topic": "Algorithms",
    "num_questions": 3,
    "difficulty": "medium"
  }'
```

**Expected Response**:
```json
{
  "quiz_id": "uuid",
  "quiz": "[{\"question\": \"What is Big O notation?\", \"options\": [...], \"correct_answer\": \"...\", ...}]",
  "sources": [
    {
      "source_file": "lecture1.pdf",
      "relevance_score": 0.92,
      "doc_type": "lecture_notes"
    }
  ],
  "usage": {
    "prompt_tokens": 450,
    "completion_tokens": 320,
    "total_tokens": 770
  }
}
```

**Test Validation**:
- ✅ Returns 3 questions
- ✅ Sources include processed document
- ✅ Token usage tracked

### Test 3.4: Generate Flashcards

**Endpoint**: `POST /api/rag/generate-flashcards`

```bash
curl -X POST http://localhost:8000/api/rag/generate-flashcards \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CS101_Fall_2024",
    "topic": "Big O Notation",
    "num_cards": 5
  }'
```

**Expected**: 5 flashcards with front/back/hint

### Test 3.5: Chat with RAG

**Endpoint**: `POST /api/chat/`

**Test Case 1: Normal Question (Should Work)**
```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CS101_Fall_2024",
    "message": "Can you explain what Big O notation means?"
  }'
```

**Expected**:
- ✅ Socratic response guiding understanding
- ✅ Sources from course materials
- ✅ No direct answer, asks guiding questions

**Test Case 2: Homework Request (Should Block)**
```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CS101_Fall_2024",
    "message": "Please solve this homework problem for me"
  }'
```

**Expected**:
```json
{
  "type": "blocked",
  "response": "I notice you're asking for homework help...",
  "triggered_rails": ["homework_cheating"]
}
```

**Test Validation**:
- ✅ Request blocked
- ✅ Educational guidance provided
- ✅ Explains why it was blocked

### Test 3.6: Generate Semester Plan

**Endpoint**: `POST /api/rag/generate-semester-plan`

```bash
curl -X POST http://localhost:8000/api/rag/generate-semester-plan \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CS101_Fall_2024",
    "student_id": "student_123",
    "start_date": "2024-09-01",
    "end_date": "2024-12-15",
    "exam_date": "2024-12-18",
    "learning_goals": [
      "Master sorting algorithms",
      "Understand time complexity",
      "Ace the final exam"
    ],
    "study_hours_per_week": 10
  }'
```

**Expected**:
- ✅ Week-by-week study plan
- ✅ Spaced repetition schedule
- ✅ Exam preparation timeline

---

## 4. Learning System Tests

### Test 4.1: Health Check

**Endpoint**: `GET /api/learning/health`

```bash
curl http://localhost:8000/api/learning/health
```

**Expected**:
```json
{
  "status": "healthy",
  "service": "learning_management_system",
  "features": [
    "spaced_repetition (FSRS)",
    "practice_sessions",
    "question_bank",
    "skill_tracking",
    "analytics",
    "syllabus_alignment"
  ]
}
```

### Test 4.2: Generate Skills from Syllabus

**Endpoint**: `POST /api/learning/skills/generate`

```bash
curl -X POST http://localhost:8000/api/learning/skills/generate \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CS101_Fall_2024",
    "syllabus_text": "Course Objectives: 1. Understand fundamental data structures including arrays, linked lists, trees, and graphs. 2. Master sorting algorithms: quicksort, mergesort, heapsort. 3. Analyze time and space complexity using Big O notation. 4. Implement search algorithms: binary search, depth-first search, breadth-first search. 5. Apply dynamic programming techniques to solve complex problems.",
    "syllabus_transcription_id": "optional-transcription-id"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "skills_created": 8,
  "skill_ids": ["skill_1", "skill_2", ...]
}
```

**Test Validation**:
- ✅ Creates 5-15 skills
- ✅ Skills have dependencies
- ✅ Linked to course materials

### Test 4.3: Generate Questions

**Endpoint**: `POST /api/learning/questions/generate`

```bash
curl -X POST http://localhost:8000/api/learning/questions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CS101_Fall_2024",
    "topics": ["Algorithms", "Data Structures"],
    "num_questions_per_topic": 10,
    "difficulty_distribution": {
      "easy": 0.3,
      "medium": 0.5,
      "hard": 0.2
    },
    "question_types": ["multiple_choice"]
  }'
```

**Expected**:
- ✅ 20 questions created (10 per topic)
- ✅ Distributed by difficulty (30% easy, 50% medium, 20% hard)
- ✅ Stored in question_bank collection

### Test 4.4: Enroll Student in Cards

**Endpoint**: `POST /api/learning/cards/enroll`

```bash
curl -X POST http://localhost:8000/api/learning/cards/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student_123",
    "course_id": "CS101_Fall_2024",
    "content_refs": ["question_1", "question_2", "question_3", "question_4", "question_5"]
  }'
```

**Expected**:
```json
{
  "success": true,
  "enrolled_count": 5,
  "card_ids": ["card_1", "card_2", "card_3", "card_4", "card_5"]
}
```

**Test Validation**:
- ✅ FSRS state initialized for each card
- ✅ Cards marked as due immediately
- ✅ Student_cards collection updated

### Test 4.5: Create Practice Session

**Endpoint**: `POST /api/learning/sessions/create`

```bash
curl -X POST http://localhost:8000/api/learning/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student_123",
    "course_id": "CS101_Fall_2024",
    "session_type": "daily_review",
    "target_card_count": 5,
    "interleaved": true
  }'
```

**Expected Response**:
```json
{
  "session_id": "session_uuid",
  "cards": [
    {
      "card_id": "card_1",
      "topic": "Algorithms",
      "difficulty": "medium",
      "question": {
        "question_text": "What is Big O notation?",
        "question_type": "multiple_choice",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "hint": "Think about time complexity"
      }
    }
  ],
  "total_cards": 5,
  "estimated_time_minutes": 10
}
```

**Test Validation**:
- ✅ Returns 5 cards
- ✅ Cards are interleaved (mixed topics)
- ✅ Session stored in database

### Test 4.6: Submit Card Review (FSRS)

**Endpoint**: `POST /api/learning/sessions/{session_id}/submit`

```bash
SESSION_ID="your-session-id"
CARD_ID="card_1"

curl -X POST "http://localhost:8000/api/learning/sessions/${SESSION_ID}/submit?student_id=student_123" \
  -H "Content-Type: application/json" \
  -d '{
    "card_id": "'${CARD_ID}'",
    "rating": 3,
    "time_spent_seconds": 45
  }'
```

**Test Different Ratings**:

**Rating 1 (Again - Forgot)**
```bash
# Expected: Very short interval (~1 day)
```

**Rating 2 (Hard - Difficult)**
```bash
# Expected: Short interval (~1-3 days)
```

**Rating 3 (Good - Correct)**
```bash
# Expected: Medium interval (~3-7 days)
```

**Rating 4 (Easy - Very Easy)**
```bash
# Expected: Long interval (~7-14 days)
```

**Expected Response**:
```json
{
  "session_id": "session_uuid",
  "cards_completed": 1,
  "total_cards": 5,
  "is_complete": false,
  "current_index": 1
}
```

**Verify FSRS Update**:
```javascript
// Check in MongoDB
db.student_cards.findOne({_id: "card_1"})

// Should see:
// - next_review updated
// - fsrs_params.stability changed
// - review_history has new entry
```

### Test 4.7: Complete Session

**Endpoint**: `POST /api/learning/sessions/{session_id}/complete`

```bash
curl -X POST "http://localhost:8000/api/learning/sessions/${SESSION_ID}/complete?student_id=student_123"
```

**Expected Response**:
```json
{
  "session_id": "session_uuid",
  "status": "completed",
  "cards_completed": 5,
  "total_cards": 5,
  "accuracy_rate": 80.0,
  "total_time_seconds": 300,
  "average_time_per_card": 60.0,
  "rating_distribution": {
    "1": 0,
    "2": 1,
    "3": 3,
    "4": 1
  },
  "topic_performance": {
    "Algorithms": {
      "presented": 3,
      "correct": 2,
      "total_time": 150
    }
  }
}
```

### Test 4.8: Get Analytics

**Endpoint**: `GET /api/learning/analytics/student`

```bash
curl "http://localhost:8000/api/learning/analytics/student?student_id=student_123&course_id=CS101_Fall_2024"
```

**Expected Response**:
```json
{
  "student_id": "student_123",
  "course_id": "CS101_Fall_2024",
  "total_cards_reviewed": 5,
  "overall_accuracy": 80.0,
  "total_time_minutes": 5,
  "active_days": 1,
  "current_streak_days": 1,
  "topic_analytics": [
    {
      "topic": "Algorithms",
      "total_attempts": 3,
      "correct_attempts": 2,
      "overall_accuracy": 66.7,
      "accuracy_by_difficulty": {
        "easy": 100.0,
        "medium": 66.7,
        "hard": 50.0
      },
      "accuracy_trend": [...]
    }
  ],
  "skills_mastered": 0,
  "skills_in_progress": 3,
  "skills_not_started": 5,
  "overall_mastery": 15.0,
  "cards_due_today": 0,
  "cards_due_this_week": 5,
  "recommended_topics": ["Data Structures"],
  "recommended_skills": ["Binary Search Trees"]
}
```

### Test 4.9: Get Skill Checklist

**Endpoint**: `GET /api/learning/skills/checklist`

```bash
curl "http://localhost:8000/api/learning/skills/checklist?student_id=student_123&course_id=CS101_Fall_2024"
```

**Expected**:
- ✅ List of all skills
- ✅ Mastery levels per skill
- ✅ Status for each (not_started, learning, etc.)
- ✅ Prerequisites shown

### Test 4.10: Syllabus Alignment

**Endpoint**: `POST /api/learning/syllabus/analyze`

```bash
curl -X POST "http://localhost:8000/api/learning/syllabus/analyze?course_id=CS101_Fall_2024&syllabus_transcription_id=syllabus_id&student_id=student_123"
```

**Expected**:
```json
{
  "course_id": "CS101_Fall_2024",
  "topics": [
    {
      "topic": "Algorithms",
      "materials_count": 3,
      "coverage_score": 85.0,
      "student_progress": 66.7,
      "sample_materials": [...]
    }
  ],
  "coverage_gaps": ["Advanced Graph Theory"],
  "overall_coverage": 80.0,
  "topics_covered": 8,
  "total_topics": 10,
  "recommendations": [
    "Add more materials for: Advanced Graph Theory",
    "Focus practice on: Data Structures"
  ]
}
```

---

## 5. Integration Tests

### Test 5.1: Complete Workflow (OCR → RAG → Learning)

**Step 1: Upload Document**
```bash
# OCR processes document
curl -X POST http://localhost:8000/api/ocr/transcribe ...
```

**Step 2: Process for RAG**
```bash
# RAG chunks and embeds
curl -X POST http://localhost:8000/api/rag/process-document ...
```

**Step 3: Generate Questions**
```bash
# RAG generates questions from materials
curl -X POST http://localhost:8000/api/learning/questions/generate ...
```

**Step 4: Enroll Student**
```bash
# Learning system creates cards
curl -X POST http://localhost:8000/api/learning/cards/enroll ...
```

**Step 5: Practice Session**
```bash
# Student practices with FSRS
curl -X POST http://localhost:8000/api/learning/sessions/create ...
```

**Step 6: View Analytics**
```bash
# Track improvement over time
curl http://localhost:8000/api/learning/analytics/student ...
```

**Test Validation**:
- ✅ Data flows through all systems
- ✅ No errors at any step
- ✅ Analytics reflect practice

### Test 5.2: Multi-Student Scenario

Test with multiple students practicing same course:

```bash
for student_id in student_001 student_002 student_003; do
  # Enroll each student
  curl -X POST http://localhost:8000/api/learning/cards/enroll \
    -H "Content-Type: application/json" \
    -d '{
      "student_id": "'$student_id'",
      "course_id": "CS101_Fall_2024",
      "content_refs": ["question_1", "question_2", "question_3"]
    }'
    
  # Each does a practice session
  # ... create session and complete reviews ...
done
```

**Test Validation**:
- ✅ FSRS state independent per student
- ✅ No data leakage between students
- ✅ Analytics separate per student

---

## 6. Performance Tests

### Test 6.1: Document Processing Speed

```bash
time curl -X POST http://localhost:8000/api/rag/process-document \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "PERF_TEST",
    "doc_type": "textbook",
    "source_file": "large_textbook.pdf",
    "ocr_text": "'$(cat large_text_file.txt)'"
  }'
```

**Expected**: < 5 seconds for 10KB text

### Test 6.2: Quiz Generation Speed

```bash
time curl -X POST http://localhost:8000/api/rag/generate-quiz \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "PERF_TEST",
    "topic": "Algorithms",
    "num_questions": 10,
    "difficulty": "medium"
  }'
```

**Expected**: 5-10 seconds with GPT-4

### Test 6.3: Session Creation Speed

```bash
time curl -X POST http://localhost:8000/api/learning/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "perf_test_student",
    "course_id": "PERF_TEST",
    "target_card_count": 50
  }'
```

**Expected**: < 1 second

### Test 6.4: Load Test - Concurrent Sessions

```bash
# Using Apache Bench
ab -n 100 -c 10 -p session_request.json -T application/json \
  http://localhost:8000/api/learning/sessions/create
```

**Expected**:
- ✅ All requests succeed
- ✅ Average response time < 2s
- ✅ No database errors

---

## 7. Test Data

### Sample Course Materials

```json
{
  "course_id": "TEST_CS101",
  "documents": [
    {
      "type": "syllabus",
      "content": "Course syllabus with objectives..."
    },
    {
      "type": "lecture_notes",
      "content": "Lecture 1: Introduction to Algorithms..."
    },
    {
      "type": "textbook",
      "content": "Chapter 1: Fundamentals..."
    }
  ]
}
```

### Sample Questions

```json
[
  {
    "question_text": "What is Big O notation?",
    "type": "multiple_choice",
    "options": [
      "A) A notation for algorithm complexity",
      "B) A programming language",
      "C) A data structure",
      "D) A sorting algorithm"
    ],
    "correct_answer": "A",
    "difficulty": "easy"
  }
]
```

### Sample Student Data

```json
{
  "student_id": "test_student_001",
  "course_enrollments": ["TEST_CS101"],
  "cards_enrolled": 20,
  "sessions_completed": 5
}
```

---

## Test Automation

### Run All Backend Tests

```bash
cd backend
pytest tests/ -v --cov=api
```

### Run Specific Test Suite

```bash
# OCR tests only
pytest tests/test_ocr.py -v

# RAG tests only
pytest tests/test_rag.py -v

# Learning tests only
pytest tests/test_learning.py -v
```

### Run Frontend Tests

```bash
cd frontend
npm test
```

### Continuous Integration

Example GitHub Actions workflow:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v
```

---

## Test Coverage Goals

| System | Target | Current |
|--------|--------|---------|
| OCR | 80% | TBD |
| RAG | 80% | TBD |
| Learning | 85% | TBD |
| **Overall** | **80%** | **TBD** |

---

## Reporting Issues

When reporting test failures, include:

1. **Test name** and endpoint
2. **Expected** vs **actual** response
3. **Error messages** from logs
4. **Environment** (dev/staging/prod)
5. **Steps to reproduce**

Example:
```
Test: RAG Quiz Generation
Endpoint: POST /api/rag/generate-quiz
Expected: 5 questions
Actual: Empty quiz array
Error: "No relevant chunks retrieved"
Environment: Development
Steps: 
1. Processed document TEST_2024/lecture1.pdf
2. Waited 10 seconds
3. Called generate-quiz endpoint
4. Received empty response
```

---

**Happy Testing! 🧪**

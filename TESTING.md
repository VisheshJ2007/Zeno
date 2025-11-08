# Zeno Platform - Quick Testing

Quick tests to verify all systems work.

---

## Health Checks

```bash
# Main API
curl http://localhost:8000/health
# Expected: {"ok": true, "service": "zeno-api"}

# RAG System
curl http://localhost:8000/api/rag/health
# Expected: {"status": "healthy", "components": {...}}

# Learning System
curl http://localhost:8000/api/learning/health
# Expected: {"status": "healthy", "service": "learning_management_system"}
```

---

## OCR System

```bash
# Get transcriptions
curl http://localhost:8000/api/ocr/transcriptions

# Search transcriptions
curl "http://localhost:8000/api/ocr/search?q=algorithms"

# Statistics
curl http://localhost:8000/api/ocr/statistics
```

---

## RAG System

### 1. Process Document

```bash
curl -X POST http://localhost:8000/api/rag/process-document \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "TEST_2024",
    "doc_type": "lecture_notes",
    "source_file": "test.pdf",
    "ocr_text": "Introduction to algorithms. Topics: sorting, searching, Big O notation.",
    "metadata": {"topic": "Algorithms"}
  }'
```

### 2. Generate Quiz

```bash
curl -X POST http://localhost:8000/api/rag/generate-quiz \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "TEST_2024",
    "topic": "Algorithms",
    "num_questions": 3,
    "difficulty": "medium"
  }'
```

### 3. Chat with Tutor

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "TEST_2024",
    "message": "What is Big O notation?"
  }'
```

### 4. Test Guardrails

```bash
# Should be allowed
curl -X POST "http://localhost:8000/api/chat/test-guardrails?message=explain%20algorithms"

# Should be blocked
curl -X POST "http://localhost:8000/api/chat/test-guardrails?message=solve%20my%20homework"
```

---

## Learning Management System

### 1. Generate Questions

```bash
curl -X POST http://localhost:8000/api/learning/questions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "TEST_2024",
    "topics": ["Algorithms"],
    "num_questions_per_topic": 5
  }'
```

### 2. Enroll in Cards

```bash
# Replace QUESTION_IDS with actual IDs from step 1
curl -X POST http://localhost:8000/api/learning/cards/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student_123",
    "course_id": "TEST_2024",
    "content_refs": ["QUESTION_ID_1", "QUESTION_ID_2"]
  }'
```

### 3. Create Practice Session

```bash
curl -X POST http://localhost:8000/api/learning/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student_123",
    "course_id": "TEST_2024",
    "session_type": "daily_review",
    "target_card_count": 5
  }'
```

### 4. View Analytics

```bash
curl "http://localhost:8000/api/learning/analytics/student?student_id=student_123&course_id=TEST_2024"
```

### 5. Generate Skills from Syllabus

```bash
curl -X POST http://localhost:8000/api/learning/skills/generate \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "TEST_2024",
    "syllabus_text": "Course objectives: 1) Master sorting algorithms 2) Understand Big O notation 3) Apply dynamic programming"
  }'
```

---

## Complete Workflow Test

```bash
# 1. Process document
curl -X POST http://localhost:8000/api/rag/process-document \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "WORKFLOW_TEST",
    "doc_type": "lecture_notes",
    "source_file": "lecture1.pdf",
    "ocr_text": "Sorting algorithms include bubble sort, merge sort, and quick sort. Time complexity varies from O(n²) to O(n log n).",
    "metadata": {"topic": "Sorting"}
  }'

# 2. Generate questions
curl -X POST http://localhost:8000/api/learning/questions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "WORKFLOW_TEST",
    "topics": ["Sorting"],
    "num_questions_per_topic": 3
  }'

# 3. Wait a few seconds, then generate quiz
curl -X POST http://localhost:8000/api/rag/generate-quiz \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "WORKFLOW_TEST",
    "topic": "Sorting",
    "num_questions": 3,
    "difficulty": "medium"
  }'
```

---

## Frontend Testing

Open browser to:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs (interactive Swagger UI)

Test in Swagger UI:
1. Click any endpoint
2. Click "Try it out"
3. Fill in parameters
4. Click "Execute"

---

## Common Issues

**"No relevant chunks retrieved"**
- Process at least one document first
- Wait 10-20 seconds for embedding processing
- Verify `course_id` matches

**"Vector index not found"**
- Create index in MongoDB Atlas UI
- See [SETUP.md](./SETUP.md) Step 3

**"Azure OpenAI unhealthy"**
- Check API keys in `.env`
- Verify models are deployed

---

## Performance Testing

```bash
# Time a request
time curl http://localhost:8000/api/rag/health

# Expected: < 1 second

# Check token usage in response
curl -X POST http://localhost:8000/api/rag/generate-quiz ... | grep usage
```

---

**For full testing guide, see:** [TESTING_GUIDE.md](./TESTING_GUIDE.md)

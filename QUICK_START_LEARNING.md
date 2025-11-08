# Quick Start: Learning Management System

## 🚀 Get Started in 5 Minutes

### Step 1: Setup Database (one-time)
```bash
cd backend
python -m api.learning.setup_indexes
```

### Step 2: Start the System
```bash
# Backend
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm run dev
```

### Step 3: Test the System
```bash
# Health check
curl http://localhost:8000/api/learning/health

# Expected response:
# {"status": "healthy", "service": "learning_management_system", ...}
```

---

## 📝 Basic Usage Flow

### 1. Upload Syllabus & Generate Skills
```typescript
// Upload syllabus via existing OCR
const syllabusResult = await ocrService.processDocument(syllabusFile);

// Generate skills from syllabus
const skillsResult = await learningService.generateSkills({
  course_id: "CS101_Fall_2024",
  syllabus_text: syllabusResult.cleaned_text,
  syllabus_transcription_id: syllabusResult.transcription_id
});
// ✅ Creates 10-20 skills with dependencies
```

### 2. Generate Questions
```typescript
const questionsResult = await learningService.generateQuestions({
  course_id: "CS101_Fall_2024",
  topics: ["Algorithms", "Data Structures"],
  num_questions_per_topic: 10
});
// ✅ Creates 20 questions via RAG
```

### 3. Enroll Student
```typescript
await learningService.enrollInCards({
  student_id: "student_123",
  course_id: "CS101_Fall_2024",
  content_refs: questionsResult.question_ids
});
// ✅ Initializes FSRS state for each card
```

### 4. Practice Session (React Component)
```tsx
import { PracticeSession } from '@/components/learning/PracticeSession';

<PracticeSession
  studentId="student_123"
  courseId="CS101_Fall_2024"
  onComplete={(summary) => console.log(summary)}
/>
```

### 5. View Analytics
```tsx
import { AnalyticsDashboard } from '@/components/learning/AnalyticsDashboard';

<AnalyticsDashboard
  studentId="student_123"
  courseId="CS101_Fall_2024"
/>
```

### 6. View Skills
```tsx
import { SkillChecklist } from '@/components/learning/SkillChecklist';

<SkillChecklist
  studentId="student_123"
  courseId="CS101_Fall_2024"
/>
```

---

## 🎯 What You Get

### ✅ FSRS Spaced Repetition
- **Modern algorithm** (better than SM-2)
- Optimal review scheduling
- Adaptive to individual performance

### ✅ Interleaved Practice
- Mix topics for better retention
- +20% improvement vs blocked practice

### ✅ Topic Accuracy Analytics (Primary Focus)
- Track accuracy over time
- See improvement as difficulty increases
- Weekly trends with difficulty breakdown

### ✅ Skill Checklist
- Course objectives from syllabus
- Mastery tracking (0-100%)
- Prerequisites and dependencies

### ✅ RAG Integration
- Auto-generate questions from materials
- Extract skills from syllabus
- Suggest materials for topics

---

## 📊 Key Endpoints

```
POST /api/learning/cards/enroll             # Enroll in cards
POST /api/learning/sessions/create          # Start practice
GET  /api/learning/analytics/student        # Get analytics
GET  /api/learning/skills/checklist         # Get skills
POST /api/learning/questions/generate       # Generate questions
POST /api/learning/skills/generate          # Generate skills
```

---

## 🔍 Troubleshooting

**No cards due?**
```bash
# Check if student is enrolled
curl "http://localhost:8000/api/learning/cards/statistics?student_id=student_123&course_id=CS101"
```

**Questions not generating?**
```bash
# Check RAG health
curl http://localhost:8000/api/rag/health
```

**Need more help?**
See `LEARNING_SYSTEM_SETUP.md` for comprehensive documentation.

---

## 📚 Files Created

**Backend:**
- `backend/api/learning/*.py` (10 files, ~4,000 lines)
- `backend/api/routes/learning_routes.py` (600 lines)

**Frontend:**
- `frontend/services/learningService.ts` (600 lines)
- `frontend/components/learning/*.tsx` (3 components, ~1,100 lines)

**Documentation:**
- `LEARNING_SYSTEM_SETUP.md` (comprehensive guide)
- `IMPLEMENTATION_SUMMARY.md` (what was built)
- `QUICK_START_LEARNING.md` (this file)

---

**🎉 Ready to enhance learning outcomes with data-driven spaced repetition!**

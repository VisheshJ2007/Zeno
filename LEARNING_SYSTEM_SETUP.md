# Zeno Learning Management System - Setup Guide

## Overview

The Learning Management System (LMS) adds advanced educational features to Zeno:

- **FSRS Spaced Repetition**: Modern algorithm for optimal review scheduling
- **Interleaved Practice**: Mix topics for better retention
- **Skill Tracking**: Monitor mastery of course objectives
- **Topic Analytics**: Track accuracy trends over time and difficulty
- **RAG-Powered Generation**: Auto-generate questions and extract skills from syllabus
- **Syllabus Alignment**: Cross-check materials with course syllabus

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  EXISTING: OCR-RAG PIPELINE (Document Processing)      │
│  • Document intake, transcription, vector storage       │
└──────────────────┬──────────────────────────────────────┘
                   │ feeds content
                   ↓
┌─────────────────────────────────────────────────────────┐
│  NEW: LEARNING MANAGEMENT SYSTEM                        │
│  • Spaced Repetition (FSRS)                            │
│  • Practice Sessions (Interleaved)                      │
│  • Question Bank                                        │
│  • Skill Tracking & Analytics                          │
│  • Syllabus Alignment                                   │
└─────────────────────────────────────────────────────────┘
```

**Key Design Principles:**
- ✅ Separation of Concerns: OCR-RAG for content, LMS for learning
- ✅ RAG Integration: LMS uses processed materials via vector search
- ✅ No Changes to Existing Pipeline: OCR-RAG continues to work as-is

---

## Installation

### 1. Backend Setup

#### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

*Note: The LMS uses existing dependencies (FastAPI, MongoDB, Azure OpenAI). No additional packages needed.*

#### Create Database Indexes
```bash
python -m api.learning.setup_indexes
```

This creates optimized indexes for:
- `student_cards`
- `practice_sessions`
- `question_bank`
- `skills`
- `student_skill_progress`
- `syllabus_alignment`

#### Environment Variables

Ensure your `.env` file has:
```env
# MongoDB (existing)
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=zeno_db

# Azure OpenAI (existing)
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_CHAT_DEPLOYMENT=gpt-4
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

*Note: All necessary packages are already in package.json*

---

## Quick Start Usage

### Step 1: Upload and Process Syllabus

```typescript
// 1. Upload syllabus via OCR (existing)
const syllabusResult = await ocrService.processDocument(syllabusFile);

// 2. Generate skills from syllabus (new)
const skillsResult = await learningService.generateSkills({
  course_id: "CS101_Fall_2024",
  syllabus_text: syllabusResult.cleaned_text,
  syllabus_transcription_id: syllabusResult.transcription_id
});
// Creates: ~10-20 skills with dependencies, estimated hours, materials links
```

### Step 2: Generate Questions

```typescript
// Generate questions from course materials via RAG
const questionsResult = await learningService.generateQuestions({
  course_id: "CS101_Fall_2024",
  topics: ["Algorithms", "Data Structures", "Complexity"],
  num_questions_per_topic: 10,
  difficulty_distribution: {
    easy: 0.3,
    medium: 0.5,
    hard: 0.2
  }
});
// Creates: 30 questions (10 per topic) stored in question_bank
```

### Step 3: Enroll Student in Cards

```typescript
// Enroll student in flashcard/question practice
const enrollResult = await learningService.enrollInCards({
  student_id: "student_123",
  course_id: "CS101_Fall_2024",
  content_refs: questionsResult.question_ids  // Questions to practice
});
// Initializes FSRS state for each card
```

### Step 4: Practice Session

```tsx
// Use PracticeSession component
import { PracticeSession } from '@/components/learning/PracticeSession';

<PracticeSession
  studentId="student_123"
  courseId="CS101_Fall_2024"
  sessionType="daily_review"
  onComplete={(summary) => {
    console.log(`Accuracy: ${summary.accuracy_rate}%`);
  }}
/>
```

**Practice Flow:**
1. Creates interleaved session with due cards
2. Student answers each question
3. Rates difficulty (1=Again, 2=Hard, 3=Good, 4=Easy)
4. FSRS calculates next review date
5. Updates skill mastery based on performance

### Step 5: View Analytics

```tsx
// Analytics Dashboard
import { AnalyticsDashboard } from '@/components/learning/AnalyticsDashboard';

<AnalyticsDashboard
  studentId="student_123"
  courseId="CS101_Fall_2024"
/>
```

**Shows:**
- Overall accuracy and trends
- Topic-level performance with difficulty breakdown
- Skill mastery progress
- Study streaks and time invested
- Recommendations for topics/skills

### Step 6: Skill Checklist

```tsx
// Skill Checklist
import { SkillChecklist } from '@/components/learning/SkillChecklist';

<SkillChecklist
  studentId="student_123"
  courseId="CS101_Fall_2024"
/>
```

**Shows:**
- All course skills organized by topic
- Mastery level (0-100%) per skill
- Status: not_started, learning, reviewing, mastered
- Prerequisites and dependencies
- Time spent and accuracy per skill

---

## API Endpoints Reference

### Cards Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/learning/cards/enroll` | POST | Enroll student in cards |
| `/api/learning/cards/{id}/review` | POST | Submit card review (FSRS) |
| `/api/learning/cards/due` | GET | Get due cards |
| `/api/learning/cards/statistics` | GET | Get card stats |

### Practice Sessions

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/learning/sessions/create` | POST | Create practice session |
| `/api/learning/sessions/{id}/submit` | POST | Submit card response |
| `/api/learning/sessions/{id}/complete` | POST | Complete session |
| `/api/learning/sessions/{id}` | GET | Get session details |
| `/api/learning/sessions/history` | GET | Get session history |

### Question Bank

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/learning/questions/create` | POST | Create question |
| `/api/learning/questions/generate` | POST | Generate via RAG |
| `/api/learning/questions/by-topic` | GET | Get by topic |

### Skills

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/learning/skills/generate` | POST | Generate from syllabus |
| `/api/learning/skills/checklist` | GET | Get skill checklist |
| `/api/learning/skills/recommended` | GET | Get recommendations |

### Analytics

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/learning/analytics/student` | GET | Student dashboard |
| `/api/learning/analytics/topics` | GET | Topic accuracy trends |

### Syllabus Alignment

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/learning/syllabus/analyze` | POST | Analyze coverage |
| `/api/learning/syllabus/alignment` | GET | Get alignment report |
| `/api/learning/syllabus/suggest-materials` | GET | Suggest materials |

---

## FSRS Spaced Repetition

### How It Works

The Free Spaced Repetition Scheduler (FSRS) is a modern algorithm that optimizes review intervals:

**Key Concepts:**
- **Stability**: How long a memory lasts (in days)
- **Difficulty**: How hard the material is (1-10 scale)
- **Retrievability**: Probability of recall at any moment

**Rating Scale:**
- `1 = Again`: Completely forgot, review immediately
- `2 = Hard`: Remembered with significant difficulty
- `3 = Good`: Remembered correctly
- `4 = Easy`: Remembered easily and quickly

**Algorithm:**
1. New card → Initial stability based on rating (Again: 0.4d, Good: 2.4d, Easy: 5.8d)
2. Each review → Calculates new stability and next interval
3. Forgetting curve → Adjusts for individual performance
4. Memory model → Predicts optimal review timing

**Example Schedule:**
```
Card: "What is a binary search tree?"

Review 1: Rating = GOOD (3)
  → Next review: 2.4 days

Review 2: Rating = GOOD (3)
  → Stability increases
  → Next review: 7 days

Review 3: Rating = EASY (4)
  → Stability increases significantly
  → Next review: 21 days

Review 4: Rating = AGAIN (1)
  → Forgot! Stability decreases
  → Next review: 1 day (relearn)
```

### Why FSRS > SM-2

| Feature | SM-2 (Anki old) | FSRS (Modern) |
|---------|-----------------|---------------|
| Memory model | Simple intervals | Exponential forgetting |
| Difficulty | Fixed per card | Adapts to performance |
| Retrieval | Not modeled | Explicitly tracked |
| Accuracy | ~80% prediction | ~90% prediction |
| Personalization | Limited | High |

---

## Interleaved Practice

**Research-Backed Approach:**

Instead of:
```
Math: Q1, Q2, Q3, Q4
Physics: Q5, Q6, Q7, Q8
Chemistry: Q9, Q10
```

We do:
```
Math Q1 → Physics Q5 → Chemistry Q9 → Math Q2 → Physics Q6 → ...
```

**Benefits:**
- **+20% retention** compared to blocked practice
- Improves discrimination between concepts
- Better long-term learning

**Implementation:**
- Round-robin topic selection
- 20% randomness to avoid predictability
- Respects due dates (most overdue first)

---

## Analytics & Topic Accuracy

### What We Track

**Per Topic:**
- Overall accuracy
- Accuracy by difficulty (easy/medium/hard)
- Weekly accuracy trends
- Response times
- Number of attempts

**Per Skill:**
- Mastery level (0-100%)
- Practice attempts and accuracy
- Time spent
- Status progression (not_started → learning → reviewing → mastered)

**Per Student:**
- Overall accuracy and trends (7-day, 30-day)
- Study streaks and active days
- Cards due today/this week
- Time invested
- Recommended topics and skills

### Example Analytics Output

```json
{
  "topic": "Algorithms",
  "overall_accuracy": 76.5,
  "accuracy_by_difficulty": {
    "easy": 92.3,
    "medium": 78.1,
    "hard": 58.2
  },
  "accuracy_trend": [
    {
      "date": "2024-01-01",
      "accuracy_rate": 65.0,
      "predominant_difficulty": "easy"
    },
    {
      "date": "2024-01-08",
      "accuracy_rate": 71.5,
      "predominant_difficulty": "medium"
    },
    {
      "date": "2024-01-15",
      "accuracy_rate": 76.5,
      "predominant_difficulty": "hard"
    }
  ]
}
```

**Key Insight:** See accuracy improvement as difficulty increases = effective learning!

---

## Database Collections

### `student_cards`
Stores each student's enrolled cards with FSRS state.

**Key Fields:**
- `student_id`, `course_id`, `content_ref` (question_id)
- `fsrs_params`: {stability, difficulty, reps, lapses, state}
- `next_review`: When this card is due
- `review_history`: Array of all reviews
- `accuracy_rate`, `total_reviews`, `correct_reviews`

**Indexes:**
- `(student_id, next_review)` - Fast due card queries
- `(student_id, course_id)` - Student's cards
- `topic`, `skills` - Filter by topic/skill

### `practice_sessions`
Tracks practice sessions.

**Key Fields:**
- `session_id`, `student_id`, `course_id`
- `card_ids`: Cards in session (interleaved order)
- `card_responses`: Array of responses
- `rating_distribution`: {1: n, 2: n, 3: n, 4: n}
- `topic_performance`: Performance by topic

**Indexes:**
- `(student_id, started_at)` - Session history
- `status` - Active sessions

### `question_bank`
Persistent question storage with analytics.

**Key Fields:**
- `question_id`, `course_id`
- `question_text`, `options`, `correct_answer`, `explanation`
- `topics`, `skills_tested`, `difficulty_rated`, `bloom_level`
- `times_presented`, `accuracy_rate`, `average_time_seconds`
- `difficulty_actual`: IRT-calibrated difficulty

**Indexes:**
- `course_id`, `topics`, `skills_tested`
- `difficulty_rated`, `accuracy_rate`

### `skills`
Course learning objectives.

**Key Fields:**
- `skill_id`, `course_id`, `name`, `description`
- `topic`, `difficulty`, `prerequisites[]`
- `source_materials`: Links to RAG chunks
- `assessment_questions`: Question IDs testing this skill

**Indexes:**
- `course_id`, `topic`, `difficulty`
- `prerequisites`

### `student_skill_progress`
Tracks mastery per skill per student.

**Key Fields:**
- `student_id`, `skill_id`, `course_id`
- `status`: not_started | learning | reviewing | mastered
- `mastery_level`: 0-100%
- `practice_attempts`, `correct_count`, `accuracy_rate`
- `time_spent_minutes`, `last_practiced`

**Indexes:**
- `(student_id, skill_id)` - Unique per student-skill
- `(student_id, course_id, status)` - Filter by status

### `syllabus_alignment`
Syllabus coverage analysis.

**Key Fields:**
- `course_id`, `syllabus_transcription_id`, `student_id`
- `topics[]`: Coverage per topic
- `coverage_gaps[]`: Topics with insufficient materials
- `overall_coverage`: 0-100%
- `recommendations[]`

---

## Troubleshooting

### No cards due for review

**Problem:** Session creation returns "No cards due for review"

**Solutions:**
1. Enroll student in cards first:
   ```typescript
   await learningService.enrollInCards({...})
   ```
2. Check `next_review` dates in database:
   ```javascript
   db.student_cards.find({student_id: "...", next_review: {$lte: new Date()}})
   ```

### FSRS not scheduling correctly

**Problem:** Cards always due immediately or too far apart

**Solutions:**
1. Verify FSRS parameters are initialized:
   ```javascript
   db.student_cards.findOne({}, {fsrs_params: 1})
   // Should have: stability, difficulty, reps, state
   ```
2. Check review ratings are 1-4:
   ```typescript
   await learningService.reviewCard(cardId, studentId, {
     rating: 3,  // Must be 1, 2, 3, or 4
     time_spent_seconds: 30
   })
   ```

### Question generation fails

**Problem:** `generateQuestions` returns empty array

**Solutions:**
1. Ensure course has materials in `course_materials` collection
2. Check RAG system health:
   ```bash
   curl http://localhost:8000/api/rag/health
   ```
3. Verify Azure OpenAI credentials in `.env`

### Analytics showing zero

**Problem:** Dashboard shows 0 for all metrics

**Solutions:**
1. Student must complete at least one practice session
2. Check session was marked as "completed":
   ```javascript
   db.practice_sessions.find({student_id: "...", status: "completed"})
   ```

---

## Performance Considerations

### Database Indexes

All critical queries are indexed:
- Due card lookups: `O(log n)` with `(student_id, next_review)` index
- Session history: `O(log n)` with `(student_id, started_at)` index
- Topic queries: `O(1)` with topic index

### Caching Recommendations

For production at scale:
1. **Redis for due counts:**
   ```
   Key: `due_count:{student_id}:{course_id}`
   TTL: 1 hour
   ```
2. **Skill graphs:** Cache after generation (rarely changes)
3. **Analytics:** Compute daily, cache for 24h

### RAG Token Usage

**Question Generation:**
- Per topic: ~500-800 tokens
- Cost: ~$0.01 per 10 questions (GPT-4)

**Skill Extraction:**
- Per syllabus: ~1000-1500 tokens
- Cost: ~$0.02 per syllabus (GPT-4)

**Optimization:**
- Use GPT-3.5-turbo for initial extraction
- Use GPT-4 only for refinement
- Cache generated content

---

## Next Steps

### Recommended Implementation Order

1. **Week 1: Core System**
   - Set up database indexes
   - Test question generation
   - Test skill extraction from syllabus

2. **Week 2: Practice Flow**
   - Implement enrollment flow
   - Test practice sessions
   - Verify FSRS scheduling

3. **Week 3: Analytics**
   - Build analytics dashboard
   - Implement skill checklist
   - Test syllabus alignment

4. **Week 4: Optimization**
   - Add caching layer
   - Optimize database queries
   - Performance testing

### Future Enhancements

**Short-term (1-2 months):**
- [ ] Mobile-responsive components
- [ ] Notification system for due cards
- [ ] Export progress reports (PDF)
- [ ] Gamification (badges, streaks)

**Long-term (3-6 months):**
- [ ] Multi-language support
- [ ] Collaborative learning features
- [ ] Advanced IRT difficulty calibration
- [ ] AI tutoring with Socratic method
- [ ] Adaptive testing

---

## Support & Resources

### Documentation
- FSRS Algorithm: https://github.com/open-spaced-repetition/fsrs4anki/wiki/ABC-of-FSRS
- MongoDB Vector Search: https://www.mongodb.com/docs/atlas/atlas-vector-search/
- Azure OpenAI: https://learn.microsoft.com/azure/ai-services/openai/

### Contact
- Report issues: Create GitHub issue
- Questions: Check documentation first
- Feature requests: Submit via GitHub discussions

---

## License

Same as Zeno platform.

---

**Built with ❤️ for better learning outcomes**

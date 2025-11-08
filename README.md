# Zeno AI Tutoring Platform

AI-powered learning platform with OCR processing, RAG content generation, and spaced repetition learning.

---

## 🎯 Features

### OCR Document Processing
- Client-side Tesseract.js OCR
- Intelligent text cleaning (50+ error fixes)
- Auto-detect document type & subject
- MongoDB full-text search

### RAG Content Generation
- Azure OpenAI (GPT-4 + embeddings)
- MongoDB Atlas vector search
- Generate: quizzes, flashcards, lesson plans, exams
- Educational guardrails (prevent homework cheating)
- Socratic tutoring chat

### Learning Management System
- **FSRS Spaced Repetition** - 90% accuracy (vs 80% for SM-2)
- **Interleaved Practice** - +20% retention
- **Question Bank** - RAG-generated with IRT calibration
- **Skill Tracking** - Checklist with mastery levels
- **Topic Analytics** - Accuracy over time
- **Syllabus Alignment** - Coverage gap analysis

---

## 🚀 Quick Start

**Required:** MongoDB Atlas + Azure OpenAI API keys

```bash
# 1. Setup API keys
# See API_KEYS.md for where to get keys
cd backend
cp .env.example .env
# Edit .env with your keys

# 2. Install & run backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m api.rag.mongodb_setup
python -m api.learning.setup_indexes
uvicorn main:app --reload

# 3. Install & run frontend
cd ../frontend
npm install
npm run dev

# 4. Verify
curl http://localhost:8000/health
```

**⚠️ Don't forget:** Create vector search index in MongoDB Atlas UI
→ See [SETUP.md](./SETUP.md) for details

---

## 📚 Documentation

| Doc | Purpose |
|-----|---------|
| [API_KEYS.md](./API_KEYS.md) | Where to put API keys |
| [SETUP.md](./SETUP.md) | Installation guide |
| [TESTING.md](./TESTING.md) | Quick tests |
| http://localhost:8000/docs | API reference (Swagger) |

---

## 🛠️ Tech Stack

**Backend:** FastAPI, Python 3.10+, Motor (async MongoDB), Azure OpenAI
**Frontend:** Next.js 14, React 18, TypeScript, Tesseract.js, Tailwind
**Infrastructure:** MongoDB Atlas (vector search), Azure OpenAI (GPT-4 + embeddings)

---

## 📁 Project Structure

```
Zeno/
├── backend/
│   ├── api/
│   │   ├── learning/      # Learning Management System
│   │   ├── rag/           # RAG engine
│   │   ├── guardrails/    # Educational guardrails
│   │   └── routes/        # API endpoints
│   ├── routers/ocr.py     # OCR endpoints
│   └── main.py
├── frontend/
│   ├── components/learning/  # React components
│   ├── services/             # API clients
│   └── utils/                # OCR processing
└── docs/                     # Documentation
```

---

## 💰 Costs

- **Development:** Free (M0 MongoDB + Azure pay-as-you-go)
- **Production:** ~$110-280/month (M10 MongoDB $57 + Azure OpenAI $50-200)

---

## 🧪 Testing

```bash
# Quick health check
curl http://localhost:8000/api/rag/health
curl http://localhost:8000/api/learning/health

# See TESTING.md for full test suite
```

---

## 📊 Features by System

### OCR (Existing)
- Upload & process images/PDFs
- Client-side OCR with Tesseract.js
- Smart text cleaning
- MongoDB storage

### RAG (New)
- Document chunking by type
- Vector embeddings (1536-dim)
- Semantic search
- Content generation (quizzes, flashcards, etc.)
- Chat with guardrails

### Learning (New)
- FSRS spaced repetition
- Interleaved practice sessions
- Question bank with analytics
- Skill tracking & checklist
- Progress analytics
- Syllabus alignment

---

## 🔗 API Endpoints

**OCR:** `/api/ocr/*`
**RAG:** `/api/rag/*` (9 endpoints)
**Chat:** `/api/chat/*` (4 endpoints)
**Learning:** `/api/learning/*` (25+ endpoints)

**Interactive docs:** http://localhost:8000/docs

---

## 🆘 Troubleshooting

See [SETUP.md](./SETUP.md) troubleshooting section.

Common issues:
- **MongoDB connection:** Check `.env` URI and Atlas IP whitelist
- **Azure OpenAI:** Verify endpoint ends with `/` and models deployed
- **Vector index:** Must create manually in Atlas UI

---

## 📖 Learn More

- [MongoDB Atlas](https://mongodb.com/docs/atlas)
- [Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai)
- [FSRS Algorithm](https://github.com/open-spaced-repetition/fsrs4anki)

---

**Built with ❤️ for better learning outcomes**

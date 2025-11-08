# Zeno AI Tutoring Platform

> Complete learning platform with OCR document processing, RAG-powered content generation, and advanced spaced repetition learning system.

## 📋 Quick Links

- **[Setup Guide](./SETUP_GUIDE.md)** - Complete installation and configuration
- **[Testing Guide](./TESTING_GUIDE.md)** - Comprehensive testing documentation  
- **[API Documentation](http://localhost:8000/docs)** - Swagger UI (when server is running)

---

## 🎯 Overview

Zeno combines three powerful systems into one platform:

1. **OCR Document Processing** - Extract and verify text from educational documents
2. **RAG Content Generation** - AI-powered educational content from course materials
3. **Learning Management System** - Spaced repetition, skill tracking, and analytics

### Key Features

- 📄 **Client-Side OCR** - Process documents without server load
- 🧠 **RAG Integration** - Generate content from course materials
- 🎓 **FSRS Algorithm** - Modern spaced repetition (90% vs 80% accuracy)
- 📊 **Topic Analytics** - Track accuracy as difficulty increases
- 🛡️ **Educational Guardrails** - Prevent homework cheating
- 🔄 **Interleaved Practice** - Mix topics for +20% retention

---

## 🚀 Quick Start

**⚠️ Required API Keys:** MongoDB Atlas + Azure OpenAI (see [SETUP_GUIDE.md](./SETUP_GUIDE.md) Section 1)

```bash
# 1. Backend Setup
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # ⚠️ Edit with YOUR API keys!
python -m api.rag.mongodb_setup
python -m api.learning.setup_indexes
uvicorn main:app --reload

# 2. Frontend Setup
cd frontend
npm install
npm run dev

# 3. Verify
curl http://localhost:8000/health
curl http://localhost:8000/api/rag/health
curl http://localhost:8000/api/learning/health
```

⚠️ **Critical Steps:**
1. Get API keys (MongoDB + Azure OpenAI)
2. Configure `.env` with your keys
3. Create vector search index in MongoDB Atlas UI
See [SETUP_GUIDE.md](./SETUP_GUIDE.md) for details

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SETUP_GUIDE.md](./SETUP_GUIDE.md) | Complete setup for all systems |
| [TESTING_GUIDE.md](./TESTING_GUIDE.md) | Testing and test cases |
| [OCR_SYSTEM_README.md](./OCR_SYSTEM_README.md) | OCR pipeline details |

---

## 🛠️ Tech Stack

**Frontend**: Next.js 14, React 18, TypeScript, Tesseract.js, Tailwind  
**Backend**: FastAPI, Python 3.10+, Pydantic, Motor (async MongoDB)  
**Infrastructure**: MongoDB Atlas, Azure OpenAI (GPT-4 + Embeddings)

---

## 📁 Project Structure

```
Zeno/
├── backend/
│   ├── api/
│   │   ├── learning/      # Learning Management System (~4,000 lines)
│   │   ├── rag/           # RAG System
│   │   ├── guardrails/    # Educational guardrails
│   │   └── routes/        # API routes
│   ├── routers/ocr.py     # OCR endpoints
│   └── main.py
├── frontend/
│   ├── components/        # React components
│   ├── services/          # API clients
│   └── utils/             # OCR processing
└── docs/                  # Documentation
```

---

## 📊 Features by System

### OCR Document Processing
- Client-side Tesseract.js OCR
- Intelligent text cleaning (50+ error fixes)
- Auto-detect document type & subject
- Full-text search in MongoDB

### RAG Content Generation
- Intelligent chunking by document type
- Vector search with 1536-dim embeddings
- Generate: quizzes, flashcards, lesson plans, exams
- Chat with Socratic tutoring
- Educational guardrails

### Learning Management System
- **FSRS Spaced Repetition** - Optimal review scheduling
- **Interleaved Practice** - Mix topics for retention
- **Question Bank** - Persistent with IRT calibration
- **Skill Tracking** - Syllabus extraction, prerequisites
- **Analytics** - Accuracy trends by topic/difficulty
- **Syllabus Alignment** - Coverage gap analysis

---

## 🧪 Testing

```bash
# Backend tests
cd backend && pytest

# Frontend tests  
cd frontend && npm test

# Integration tests
npm run test:integration
```

See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for details.

---

## 💰 Monthly Costs (Production)

- MongoDB Atlas M10: $57
- Azure OpenAI: $50-200
- **Total**: ~$110-280/month

---

## 📖 Learn More

- MongoDB Atlas: https://mongodb.com/docs/atlas
- Azure OpenAI: https://learn.microsoft.com/azure/ai-services/openai
- FSRS Algorithm: https://github.com/open-spaced-repetition/fsrs4anki

---

**Built with ❤️ for better learning outcomes**

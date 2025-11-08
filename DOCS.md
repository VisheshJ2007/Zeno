# Zeno Platform - Documentation Index

Complete guide to all documentation for the Zeno AI Tutoring Platform.

---

## 📖 Main Documentation

### Getting Started

1. **[README.md](./README.md)** - Platform overview and quick links
   - System architecture overview
   - Feature highlights
   - Quick start commands
   - Tech stack summary

2. **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** ⭐ **START HERE FOR SETUP**
   - Complete setup for all systems (OCR, RAG, Learning)
   - MongoDB Atlas configuration (including critical vector search index)
   - Azure OpenAI setup and model deployment
   - Backend installation and database initialization
   - Frontend installation
   - System verification tests
   - Comprehensive troubleshooting

3. **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** ⭐ **COMPLETE TESTING REFERENCE**
   - OCR system tests (4 test cases)
   - RAG system tests (6 test cases with guardrails)
   - Learning Management System tests (10 test cases)
   - Complete integration workflow tests
   - Performance testing guidelines
   - Test data examples

---

## 🎯 System-Specific Documentation

### OCR Document Processing

**[OCR_SYSTEM_README.md](./OCR_SYSTEM_README.md)**
- Detailed OCR pipeline documentation
- Tesseract.js implementation details
- Text cleaning algorithms (50+ error fixes)
- Document type detection
- Subject detection
- Frontend component architecture
- API endpoints reference

### RAG Content Generation

RAG documentation is integrated into:
- **Setup**: See [SETUP_GUIDE.md](./SETUP_GUIDE.md) sections 2-4
- **Testing**: See [TESTING_GUIDE.md](./TESTING_GUIDE.md) section 4
- **API Reference**: http://localhost:8000/docs (when server running)

Key RAG features:
- Intelligent document chunking by type
- Vector search with Azure OpenAI embeddings
- Content generation (quizzes, flashcards, lesson plans)
- Educational guardrails (homework protection)
- Socratic tutoring chat

### Learning Management System

**[LEARNING_SYSTEM_SETUP.md](./LEARNING_SYSTEM_SETUP.md)**
- Complete learning system architecture
- FSRS spaced repetition algorithm details
- Interleaved practice implementation
- Topic accuracy analytics (primary feature)
- Skill tracking and checklist system
- Question bank with IRT calibration
- Analytics and progress tracking
- API reference

**[QUICK_START_LEARNING.md](./QUICK_START_LEARNING.md)**
- 5-minute quick start guide
- Basic usage flow
- Example code snippets
- React component examples

**[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)**
- What was built (5,900+ lines of code)
- File structure overview
- Module descriptions

---

## 🚀 Quick Reference by Task

### I want to...

#### Set up the platform
→ **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** - Follow steps 1-6

#### Run the system
```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm run dev
```

#### Test all features
→ **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** - Complete test suite

#### Understand the OCR pipeline
→ **[OCR_SYSTEM_README.md](./OCR_SYSTEM_README.md)** - OCR details

#### Use the learning features
→ **[QUICK_START_LEARNING.md](./QUICK_START_LEARNING.md)** - Quick start
→ **[LEARNING_SYSTEM_SETUP.md](./LEARNING_SYSTEM_SETUP.md)** - Full details

#### Generate educational content
→ **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** Section 4 - RAG examples

#### Troubleshoot issues
→ **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** Section 7 - Troubleshooting

---

## 📂 Documentation Organization

### Consolidated Documentation (Main Guides)
- ✅ **README.md** - Entry point
- ✅ **SETUP_GUIDE.md** - All system setup
- ✅ **TESTING_GUIDE.md** - All system testing
- ✅ **DOCS.md** - This file (navigation index)

### System-Specific Details
- ✅ **OCR_SYSTEM_README.md** - OCR deep dive
- ✅ **LEARNING_SYSTEM_SETUP.md** - Learning system deep dive
- ✅ **IMPLEMENTATION_SUMMARY.md** - Learning implementation details
- ✅ **QUICK_START_LEARNING.md** - Learning quick start

### Removed/Consolidated Files
- ❌ **QUICKSTART.md** - Replaced by SETUP_GUIDE.md
- ❌ **RAG_SETUP_GUIDE.md** - Merged into SETUP_GUIDE.md
- ❌ **RAG_QUICK_START.md** - Merged into SETUP_GUIDE.md and TESTING_GUIDE.md
- ❌ **RAG_IMPLEMENTATION_SUMMARY.md** - Merged into SETUP_GUIDE.md

---

## 🔗 API Documentation

### Interactive API Documentation (Swagger UI)
When server is running, visit: **http://localhost:8000/docs**

### API Endpoint Categories

#### OCR Endpoints
- `POST /api/ocr/transcribe` - Process document with OCR
- `GET /api/ocr/transcriptions` - Get all transcriptions
- `GET /api/ocr/transcription/{id}` - Get specific transcription
- `GET /api/ocr/search` - Search transcriptions
- Full list in [OCR_SYSTEM_README.md](./OCR_SYSTEM_README.md)

#### RAG Endpoints
- `POST /api/rag/process-document` - Process OCR output for RAG
- `POST /api/rag/generate-quiz` - Generate quiz questions
- `POST /api/rag/generate-flashcards` - Generate flashcards
- `POST /api/rag/generate-lesson-plan` - Generate lesson plan
- `POST /api/rag/generate-semester-plan` - Generate study plan
- `GET /api/rag/health` - RAG system health

#### Learning System Endpoints
- `POST /api/learning/cards/enroll` - Enroll in cards
- `POST /api/learning/sessions/create` - Create practice session
- `POST /api/learning/cards/{id}/review` - Submit FSRS review
- `GET /api/learning/analytics/student` - Get analytics
- `GET /api/learning/skills/checklist` - Get skill checklist
- `POST /api/learning/questions/generate` - Generate questions via RAG
- Full list in [LEARNING_SYSTEM_SETUP.md](./LEARNING_SYSTEM_SETUP.md)

#### Chat Endpoints
- `POST /api/chat/` - Chat with RAG + guardrails
- `POST /api/chat/simple` - Chat without RAG
- `POST /api/chat/test-guardrails` - Test guardrails

---

## 🎓 Learning Path for New Developers

### Day 1: Understanding the Platform
1. Read [README.md](./README.md) - Get overview
2. Read [OCR_SYSTEM_README.md](./OCR_SYSTEM_README.md) - Understand OCR pipeline
3. Skim [LEARNING_SYSTEM_SETUP.md](./LEARNING_SYSTEM_SETUP.md) - Understand learning features

### Day 2: Setup and Testing
1. Follow [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Complete setup
2. Run tests from [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Verify everything works
3. Explore http://localhost:8000/docs - Interactive API documentation

### Day 3: Development
1. Try [QUICK_START_LEARNING.md](./QUICK_START_LEARNING.md) - Use learning features
2. Review [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Understand codebase
3. Start building!

---

## 🛠️ Technology Reference

### Backend
- **FastAPI** - https://fastapi.tiangolo.com/
- **MongoDB Motor** (async) - https://motor.readthedocs.io/
- **Azure OpenAI** - https://learn.microsoft.com/azure/ai-services/openai/
- **Pydantic** - https://docs.pydantic.dev/

### Frontend
- **Next.js 14** - https://nextjs.org/docs
- **React 18** - https://react.dev/
- **Tesseract.js** - https://tesseract.projectnaptha.com/
- **TypeScript** - https://www.typescriptlang.org/docs/

### Database
- **MongoDB Atlas** - https://www.mongodb.com/docs/atlas/
- **Vector Search** - https://www.mongodb.com/docs/atlas/atlas-vector-search/

### Algorithms
- **FSRS** - https://github.com/open-spaced-repetition/fsrs4anki
- **Spaced Repetition** - https://en.wikipedia.org/wiki/Spaced_repetition

---

## 📊 System Components Map

```
Zeno Platform
│
├── OCR Document Processing
│   ├── Frontend: Tesseract.js OCR
│   ├── Backend: FastAPI endpoints
│   └── Storage: MongoDB transcriptions collection
│   └── Docs: OCR_SYSTEM_README.md
│
├── RAG Content Generation
│   ├── Document Processing: Intelligent chunking
│   ├── Embeddings: Azure OpenAI (1536-dim)
│   ├── Vector Search: MongoDB Atlas
│   ├── Generation: GPT-4 via Azure OpenAI
│   ├── Guardrails: NeMo Guardrails (homework protection)
│   └── Docs: SETUP_GUIDE.md + TESTING_GUIDE.md
│
└── Learning Management System
    ├── Spaced Repetition: FSRS algorithm
    ├── Practice Sessions: Interleaved practice
    ├── Question Bank: RAG-generated + IRT tracking
    ├── Skill Tracking: Checklist with mastery levels
    ├── Analytics: Topic accuracy over time
    └── Docs: LEARNING_SYSTEM_SETUP.md + QUICK_START_LEARNING.md
```

---

## 🔍 Finding Information

### Search by Topic

**MongoDB**
- Setup: [SETUP_GUIDE.md](./SETUP_GUIDE.md) Section 2
- Troubleshooting: [SETUP_GUIDE.md](./SETUP_GUIDE.md) Section 7
- Collections: [LEARNING_SYSTEM_SETUP.md](./LEARNING_SYSTEM_SETUP.md) Section 8

**Azure OpenAI**
- Setup: [SETUP_GUIDE.md](./SETUP_GUIDE.md) Section 3
- Configuration: [SETUP_GUIDE.md](./SETUP_GUIDE.md) Section 4
- Troubleshooting: [SETUP_GUIDE.md](./SETUP_GUIDE.md) Section 7

**FSRS Spaced Repetition**
- Algorithm: [LEARNING_SYSTEM_SETUP.md](./LEARNING_SYSTEM_SETUP.md) Section 2
- Implementation: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- Testing: [TESTING_GUIDE.md](./TESTING_GUIDE.md) Section 5

**Vector Search**
- Index Creation: [SETUP_GUIDE.md](./SETUP_GUIDE.md) Section 2, Step 5 ⚠️ CRITICAL
- Testing: [TESTING_GUIDE.md](./TESTING_GUIDE.md) Section 4
- Troubleshooting: [SETUP_GUIDE.md](./SETUP_GUIDE.md) Section 7

**Educational Guardrails**
- Overview: [LEARNING_SYSTEM_SETUP.md](./LEARNING_SYSTEM_SETUP.md) Section 7
- Testing: [TESTING_GUIDE.md](./TESTING_GUIDE.md) Section 4.4

---

## 💡 Common Questions

### Where do I start?
→ [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Complete setup walkthrough

### How do I test if everything works?
→ [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Full test suite

### What learning features are available?
→ [QUICK_START_LEARNING.md](./QUICK_START_LEARNING.md) - Quick overview
→ [LEARNING_SYSTEM_SETUP.md](./LEARNING_SYSTEM_SETUP.md) - Complete details

### How does the OCR pipeline work?
→ [OCR_SYSTEM_README.md](./OCR_SYSTEM_README.md) - Technical details

### How do I generate educational content?
→ [TESTING_GUIDE.md](./TESTING_GUIDE.md) Section 4 - RAG examples

### Something's not working, what do I do?
→ [SETUP_GUIDE.md](./SETUP_GUIDE.md) Section 7 - Comprehensive troubleshooting

### How much will this cost to run?
→ [README.md](./README.md) - Monthly cost breakdown

---

## 📝 Documentation Standards

All documentation follows these principles:
- ✅ **Complete**: Everything needed to understand and use the system
- ✅ **Consolidated**: No duplicate information across files
- ✅ **Tested**: All examples have been tested and work
- ✅ **Up-to-date**: Reflects current codebase state
- ✅ **Accessible**: Clear navigation and cross-references

---

## 🆘 Support

**Need help?**
1. Check the troubleshooting section in [SETUP_GUIDE.md](./SETUP_GUIDE.md)
2. Review relevant test cases in [TESTING_GUIDE.md](./TESTING_GUIDE.md)
3. Examine server logs for error details
4. Check the API documentation at http://localhost:8000/docs

**Found an issue?**
- Verify your setup matches [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- Check MongoDB Atlas and Azure OpenAI configurations
- Review environment variables in `.env`

---

**Last Updated**: 2025-11-08
**Platform Version**: Complete (OCR + RAG + Learning Management System)
**Total Documentation**: 7 core files, ~60,000 words

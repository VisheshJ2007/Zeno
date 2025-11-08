# Zeno OCR Document Processing System

Complete OCR system with Tesseract.js, React/Next.js frontend, FastAPI backend, and MongoDB storage.

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Setup Instructions](#setup-instructions)
- [API Documentation](#api-documentation)
- [Usage Examples](#usage-examples)
- [Project Structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## 🎯 System Overview

This OCR system allows users to:
1. Upload images (PNG, JPG, WEBP, PDF)
2. Process them with Tesseract.js OCR (client-side)
3. Clean and structure the extracted text
4. Store processed data in MongoDB
5. Query and search transcriptions

## ✨ Features

### Frontend Features
- ✅ Drag-and-drop file upload
- ✅ Multiple file support
- ✅ Real-time OCR progress tracking
- ✅ Client-side OCR processing with Tesseract.js
- ✅ Automatic text cleaning and error correction
- ✅ Document type detection
- ✅ Subject detection (math, physics, etc.)
- ✅ Beautiful Tailwind CSS UI
- ✅ Mobile responsive design

### Backend Features
- ✅ RESTful API with FastAPI
- ✅ MongoDB integration with connection pooling
- ✅ Full-text search
- ✅ User statistics
- ✅ Automatic indexing
- ✅ Error handling and logging
- ✅ Health checks

### OCR Processing
- ✅ Tesseract.js v5 (LSTM neural network)
- ✅ High accuracy text extraction
- ✅ Common OCR error correction
- ✅ Mathematical notation support
- ✅ Document structure analysis
- ✅ Confidence scoring

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 18 + Next.js 14
- **OCR Engine**: Tesseract.js 5.0
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Language**: TypeScript

### Backend
- **Framework**: FastAPI 0.109
- **Database**: MongoDB 6.0+
- **Driver**: PyMongo 4.6
- **Validation**: Pydantic 2.5
- **Language**: Python 3.10+

## 🏗️ Architecture

```
┌─────────────┐
│   Browser   │
│             │
│  Tesseract  │◄─── Client-side OCR processing
│             │
└──────┬──────┘
       │ HTTP POST
       │ (JSON)
       ▼
┌─────────────┐
│  FastAPI    │
│  Backend    │◄─── API endpoints, validation
│             │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  MongoDB    │◄─── Document storage, indexing
│             │
└─────────────┘
```

### Data Flow

1. **Upload**: User uploads image → File validated
2. **OCR**: Tesseract.js extracts text → Progress shown
3. **Clean**: Text cleaned → Errors corrected
4. **Analyze**: Document analyzed → Type/subject detected
5. **Send**: Data sent to API → Request validated
6. **Store**: Saved to MongoDB → Indexes created
7. **Response**: Transcription ID returned → Success shown

## 🚀 Setup Instructions

### Prerequisites

- **Node.js** 18+ and npm 9+
- **Python** 3.10+
- **MongoDB** 6.0+
- **Git**

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd Zeno
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your MongoDB connection string
# MONGODB_URI=mongodb://localhost:27017
```

### 3. Frontend Setup

```bash
# Navigate to frontend
cd ../frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env.local

# Edit .env.local
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 4. Start MongoDB

```bash
# Using Docker (recommended)
docker run -d -p 27017:27017 --name mongodb mongo:6.0

# Or start local MongoDB service
mongod --dbpath /path/to/data
```

### 5. Start Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000

API docs: http://localhost:8000/docs

### 6. Start Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:3000

### 7. Create Database Indexes

```bash
# Call the admin endpoint once after setup
curl -X POST http://localhost:8000/api/ocr/admin/create-indexes
```

## 📚 API Documentation

### Endpoints

#### 1. Submit Transcription

```http
POST /api/ocr/transcribe
Content-Type: application/json

{
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
    "has_formulas": true,
    "has_tables": false,
    "has_lists": true
  },
  "user_id": "user123"
}
```

**Response:**
```json
{
  "success": true,
  "transcription_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Transcription processed successfully",
  "created_at": "2025-11-07T10:30:00Z"
}
```

#### 2. Get Transcription

```http
GET /api/ocr/transcription/{transcription_id}
```

#### 3. Get User Transcriptions

```http
GET /api/ocr/user/{user_id}/transcriptions?limit=50&skip=0
```

#### 4. Search Transcriptions

```http
GET /api/ocr/search?query=calculus&user_id=user123&limit=20
```

#### 5. Get User Statistics

```http
GET /api/ocr/user/{user_id}/statistics
```

#### 6. Health Check

```http
GET /api/ocr/health
```

Full API documentation available at: http://localhost:8000/docs

## 💡 Usage Examples

### Frontend Component Usage

```tsx
import { OCRUploader } from '@/components/OCRUploader';

function MyPage() {
  const handleComplete = (result) => {
    console.log('Transcription ID:', result.transcription_id);
  };

  const handleError = (error) => {
    console.error('Error:', error);
  };

  return (
    <OCRUploader
      onTranscriptionComplete={handleComplete}
      onError={handleError}
      userId="user123"
      maxFileSize={10 * 1024 * 1024}
      maxFiles={5}
    />
  );
}
```

### Backend API Usage

```python
# Example FastAPI endpoint integration
from fastapi import FastAPI
from backend.routers.ocr import router as ocr_router

app = FastAPI()
app.include_router(ocr_router)
```

### MongoDB Query Examples

```python
from backend.database.mongodb import get_mongo_manager
from backend.database.operations import get_transcription_by_id

# Get MongoDB collection
manager = get_mongo_manager()
collection = manager.collection

# Query transcription
transcription = await get_transcription_by_id(
    collection,
    "550e8400-e29b-41d4-a716-446655440000"
)
```

## 📁 Project Structure

```
Zeno/
├── backend/
│   ├── main.py                      # FastAPI app entry point
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Environment variables template
│   ├── routers/
│   │   └── ocr.py                  # OCR API endpoints
│   ├── models/
│   │   └── transcription.py        # Pydantic models
│   ├── database/
│   │   ├── mongodb.py              # MongoDB connection manager
│   │   └── operations.py           # CRUD operations
│   └── utils/
│       └── logger.py               # Logging configuration
│
├── frontend/
│   ├── package.json                # Node dependencies
│   ├── tsconfig.json               # TypeScript config
│   ├── .env.example                # Environment variables template
│   ├── components/
│   │   ├── OCRUploader.tsx         # Main upload component
│   │   ├── ImagePreview.tsx        # File preview component
│   │   └── ProgressBar.tsx         # Progress indicator
│   ├── utils/
│   │   ├── ocrProcessor.ts         # Tesseract.js integration
│   │   ├── textCleaner.ts          # Text cleaning utilities
│   │   ├── structureAnalyzer.ts   # Document analysis
│   │   └── apiClient.ts            # Backend API client
│   └── types/
│       └── ocr.types.ts            # TypeScript types
│
└── README.md                        # This file
```

## 🔧 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Formatting

```bash
# Backend (Python)
black backend/
isort backend/

# Frontend (TypeScript)
npm run lint
npm run format
```

### Type Checking

```bash
# Backend
mypy backend/

# Frontend
npm run type-check
```

## 🐛 Troubleshooting

### MongoDB Connection Issues

**Problem**: `ConnectionFailure: Failed to connect to MongoDB`

**Solution**:
1. Check MongoDB is running: `mongod --version`
2. Verify connection string in `.env`
3. Check firewall settings
4. Try: `docker run -d -p 27017:27017 mongo:6.0`

### Tesseract.js Loading Errors

**Problem**: `Failed to load Tesseract worker`

**Solution**:
1. Check internet connection (downloads language data)
2. Clear browser cache
3. Ensure CORS is properly configured
4. Check browser console for detailed errors

### CORS Errors

**Problem**: `Access-Control-Allow-Origin` error

**Solution**:
1. Add frontend URL to `CORS_ORIGINS` in backend `.env`
2. Restart backend server
3. Check `allow_origins` in `main.py`

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'routers'`

**Solution**:
1. Create `__init__.py` files in directories:
   ```bash
   touch backend/routers/__init__.py
   touch backend/models/__init__.py
   touch backend/database/__init__.py
   ```
2. Restart backend server

### High Memory Usage

**Problem**: Tesseract.js uses too much memory

**Solution**:
1. Limit max file size in component props
2. Process files one at a time
3. Call `processor.terminate()` when done
4. Use `getGlobalOCRProcessor()` for singleton pattern

## 🔒 Security Notes

- Never commit `.env` files
- Use environment variables for sensitive data
- Validate file types and sizes
- Sanitize user inputs
- Use HTTPS in production
- Implement rate limiting
- Add authentication/authorization

## 🚀 Production Deployment

### Environment Variables

```bash
# Production backend .env
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=zeno_production
ENVIRONMENT=production
LOG_LEVEL=WARNING

# Production frontend .env
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
NEXT_PUBLIC_ENVIRONMENT=production
```

### Docker Deployment

```dockerfile
# Backend Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Frontend Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## 📝 License

[Your License Here]

## 🤝 Contributing

[Contribution guidelines if applicable]

## 📧 Support

For issues or questions:
- Create an issue on GitHub
- Email: support@yourdomain.com

---

**Built with ❤️ using FastAPI, React, Tesseract.js, and MongoDB**

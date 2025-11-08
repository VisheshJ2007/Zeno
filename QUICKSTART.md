# Quick Start Guide - Zeno OCR System

Get the OCR system up and running in 5 minutes!

## Prerequisites

✅ Python 3.10+
✅ Node.js 18+
✅ MongoDB 6.0+ (or Docker)

## Step 1: Start MongoDB (30 seconds)

**Option A: Using Docker (Recommended)**
```bash
docker run -d -p 27017:27017 --name mongodb mongo:6.0
```

**Option B: Local MongoDB**
```bash
mongod --dbpath /your/data/path
```

## Step 2: Backend Setup (2 minutes)

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Start the backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend running at: **http://localhost:8000**
API docs at: **http://localhost:8000/docs**

## Step 3: Create Database Indexes (10 seconds)

In a new terminal:
```bash
curl -X POST http://localhost:8000/api/ocr/admin/create-indexes
```

## Step 4: Frontend Setup (2 minutes)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local

# Start the frontend
npm run dev
```

Frontend running at: **http://localhost:3000**

## Step 5: Test the System! 🎉

1. Open http://localhost:3000 in your browser
2. Drag and drop an image file (or click to upload)
3. Click "Transcribe Documents"
4. Watch the magic happen! ✨

## Verify Everything Works

### Test Backend Health
```bash
curl http://localhost:8000/health
# Should return: {"ok": true, "service": "zeno-api"}

curl http://localhost:8000/api/ocr/health
# Should return MongoDB health status
```

### Test API Documentation
Visit: http://localhost:8000/docs

Try the interactive API documentation!

## Common Issues

### MongoDB Connection Failed
```bash
# Check MongoDB is running
docker ps | grep mongodb
# OR
mongod --version
```

### Port Already in Use
```bash
# Backend on different port
uvicorn main:app --reload --port 8001

# Frontend on different port
npm run dev -- -p 3001
```

### Module Import Errors
```bash
# Make sure __init__.py files exist
ls backend/routers/__init__.py
ls backend/models/__init__.py
ls backend/database/__init__.py
```

## Environment Variables

### Backend (.env)
```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=zeno_db
MONGODB_COLLECTION=transcriptions
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## What You Get

✅ **Complete OCR Pipeline**
- Upload images (PNG, JPG, WEBP, PDF)
- Client-side OCR with Tesseract.js
- Automatic text cleaning
- Document analysis
- MongoDB storage

✅ **Production-Ready Code**
- Type-safe TypeScript
- Pydantic validation
- Error handling
- Logging
- Health checks

✅ **Beautiful UI**
- Drag-and-drop upload
- Real-time progress
- File previews
- Toast notifications
- Mobile responsive

## Next Steps

1. **Read the full documentation**: `OCR_SYSTEM_README.md`
2. **Explore the API**: http://localhost:8000/docs
3. **Customize the UI**: Edit `frontend/components/OCRUploader.tsx`
4. **Add authentication**: Implement user auth in your app
5. **Deploy to production**: Follow deployment guide in README

## File Structure Quick Reference

```
backend/
  main.py              ← Start here
  routers/ocr.py       ← API endpoints
  models/              ← Pydantic models
  database/            ← MongoDB operations

frontend/
  components/          ← React components
  utils/               ← OCR processing
  types/               ← TypeScript types
```

## Testing

Upload a test image with text (lecture notes, book page, document scan) and verify:

1. ✅ File uploads successfully
2. ✅ Progress bar shows OCR processing
3. ✅ Text is extracted and displayed
4. ✅ Transcription ID is returned
5. ✅ Data appears in MongoDB

Check MongoDB:
```bash
# Connect to MongoDB
mongosh

# Switch to database
use zeno_db

# Check transcriptions
db.transcriptions.find().pretty()
```

## Support

Need help? Check:
- Full README: `OCR_SYSTEM_README.md`
- API docs: http://localhost:8000/docs
- GitHub issues

---

**Happy coding! 🚀**

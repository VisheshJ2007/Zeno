# API Keys Setup - Where to Insert Credentials

## ✅ One File to Edit: `backend/.env`

**File location:** `/home/triumviratesys/Zeno/backend/.env`

This file already exists. You just need to replace the placeholder values with your actual credentials.

---

## 🔑 Step 1: MongoDB Connection String

**Lines 3-5 in `backend/.env`:**

### Option A: Local MongoDB (for testing)
Leave as is if you have MongoDB running locally:
```env
MONGODB_URI=mongodb://localhost:27017
```

### Option B: MongoDB Atlas (recommended)
Replace with your Atlas connection string:
```env
MONGODB_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@YOUR_CLUSTER.mongodb.net/?retryWrites=true&w=majority
```

**Example:**
```env
MONGODB_URI=mongodb+srv://john:MySecurePass123@cluster0.mongodb.net/?retryWrites=true&w=majority
```

---

## 🔑 Step 2: Azure OpenAI Credentials

**Lines 15-19 in `backend/.env`:**

Replace these three lines:
```env
AZURE_OPENAI_ENDPOINT=https://YOUR_RESOURCE_NAME.openai.azure.com/
AZURE_OPENAI_KEY=YOUR_AZURE_OPENAI_KEY_HERE
AZURE_CHAT_DEPLOYMENT=gpt-4
```

**Real example:**
```env
AZURE_OPENAI_ENDPOINT=https://my-ai-resource.openai.azure.com/
AZURE_OPENAI_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
AZURE_CHAT_DEPLOYMENT=gpt-4
```

**Where to get these:**
1. Go to https://portal.azure.com
2. Find your Azure OpenAI resource
3. Go to "Keys and Endpoint"
4. Copy:
   - **Endpoint** → `AZURE_OPENAI_ENDPOINT`
   - **Key 1** → `AZURE_OPENAI_KEY`
5. Make sure you deployed models:
   - `text-embedding-ada-002` (for embeddings)
   - `gpt-4` or `gpt-35-turbo` (for chat)

---

## ✅ Complete Example

After editing, your `backend/.env` should look like:

```env
# MongoDB Configuration
MONGODB_URI=mongodb+srv://john:MyPass123@cluster0.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=zeno_db
MONGODB_COLLECTION=transcriptions
# ... other MongoDB settings stay the same ...

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://my-ai-resource.openai.azure.com/
AZURE_OPENAI_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_CHAT_DEPLOYMENT=gpt-4

# Rest of the file stays the same
```

---

## 🚀 How to Run

### 1. Start Backend
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

**Wait for:**
```
✓ MongoDB connection established successfully
✓ RAG system status: healthy
```

### 2. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## 🔍 Test It Works

1. **Backend health:** http://localhost:8000/health
2. **MongoDB check:** http://localhost:8000/api/ocr/health
3. **RAG check:** http://localhost:8000/api/rag/health

All should return `"status": "healthy"`

---

## 🎯 What Was Fixed (Backend Only)

The OCR pipeline now works correctly:

1. ✅ Frontend uploads document → OCR processes it
2. ✅ Backend `/api/ocr/transcribe` saves to MongoDB
3. ✅ **NEW:** Backend automatically triggers RAG processing (chunking, embeddings)
4. ✅ Documents are now searchable and ready for study plan generation
5. ✅ Frontend can now call `/api/rag/generate-semester-plan` to get study plans

**No frontend changes needed!** The existing frontend already works - the backend now handles RAG processing automatically.

---

## 🆘 Troubleshooting

| Error | Fix |
|-------|-----|
| "MongoDB connection failed" | Check `MONGODB_URI` in `backend/.env` is correct |
| "Azure OpenAI error" | Check `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` |
| "Model not found" | Make sure you deployed `text-embedding-ada-002` and `gpt-4` in Azure |
| Backend won't start | Run `cd backend && pip install -r requirements.txt` |

---

## 📝 Summary

**What to edit:** Only `backend/.env` (lines 3, 15, 16, 19)
**What changed:** Backend now auto-processes documents for RAG
**What to do:** Add your MongoDB and Azure credentials, start the servers, upload a document!

That's it! The OCR pipeline will now save transcriptions to MongoDB and automatically process them for study plan generation.

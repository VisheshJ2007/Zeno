# Zeno Platform - Complete Setup Guide

Comprehensive setup guide for OCR Document Processing, RAG Content Generation, and Learning Management System.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [MongoDB Atlas Setup](#mongodb-atlas-setup)
3. [Azure OpenAI Setup](#azure-openai-setup)
4. [Backend Installation](#backend-installation)
5. [Frontend Installation](#frontend-installation)
6. [System Verification](#system-verification)
7. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

### Required API Keys & Services

**⚠️ CRITICAL: You will need these API keys before starting:**

✅ **MongoDB Atlas Account** (Required for all features)
- Sign up: https://www.mongodb.com/cloud/atlas
- Free M0 tier works for development
- M10+ required for production vector search
- **What you'll get**: MongoDB connection string (URI)

✅ **Azure OpenAI Service** (Required for RAG + Learning features)
- Azure subscription required
- Request access: https://aka.ms/oai/access
- Deploy models: GPT-4 and text-embedding-ada-002
- **What you'll get**: API endpoint, API key, deployment names

**API Keys Summary:**
- `MONGODB_URI` - MongoDB Atlas connection string with username/password
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI resource endpoint URL
- `AZURE_OPENAI_KEY` - Azure OpenAI API key (32-64 characters)
- `AZURE_CHAT_DEPLOYMENT` - GPT-4 deployment name (usually "gpt-4")
- `AZURE_EMBEDDING_DEPLOYMENT` - Embedding deployment name (usually "text-embedding-ada-002")

**Cost Estimate:**
- MongoDB Atlas: Free (M0) or $57/month (M10)
- Azure OpenAI: ~$50-200/month depending on usage
- **Total**: $0 (dev) or ~$110-280/month (production)

### System Requirements

- Python 3.10 or higher
- Node.js 18 or higher
- Git
- 8GB RAM minimum
- 20GB disk space

---

## 2. MongoDB Atlas Setup

### Step 1: Create Cluster

1. Log in to [MongoDB Atlas](https://cloud.mongodb.com)
2. Click **Build a Database**
3. Choose cluster tier:
   - **Development**: M0 (Free, limited vector search)
   - **Production**: M10+ ($57/month, full vector search)
4. Select cloud provider and region
5. Name your cluster (e.g., `zeno-cluster`)
6. Click **Create**
7. Wait 3-5 minutes for deployment

### Step 2: Configure Network Access

1. Go to **Network Access** in left sidebar
2. Click **Add IP Address**
3. Options:
   - **Development**: Click **Allow Access from Anywhere**
   - **Production**: Add specific IP addresses
4. Click **Confirm**

### Step 3: Create Database User

1. Go to **Database Access** in left sidebar
2. Click **Add New Database User**
3. Choose **Password** authentication method
4. Set username (e.g., `zeno_user`)
5. Generate and save password
6. Set privileges: **Atlas Admin** (development) or **Read and write to any database** (production)
7. Click **Add User**

### Step 4: Get Connection String

1. Return to **Database** view
2. Click **Connect** on your cluster
3. Choose **Connect your application**
4. Select **Python** and version **3.12 or later**
5. Copy connection string
6. Replace `<password>` with your actual password

Example connection string:
```
mongodb+srv://zeno_user:YOUR_PASSWORD@zeno-cluster.abc123.mongodb.net/?retryWrites=true&w=majority
```

### Step 5: Create Vector Search Index

⚠️ **CRITICAL STEP** - Required for RAG functionality

1. Go to your cluster in Atlas
2. Click **Search** tab
3. Click **Create Search Index**
4. Choose **JSON Editor**
5. Configure:
   - **Database**: `zeno_db`
   - **Collection**: `course_materials`
   - **Index Name**: `course_materials_vector_index`

6. Paste this configuration:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "content_vector",
      "numDimensions": 1536,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "course_id"
    },
    {
      "type": "filter",
      "path": "doc_type"
    },
    {
      "type": "filter",
      "path": "metadata.topic"
    },
    {
      "type": "filter",
      "path": "metadata.difficulty"
    },
    {
      "type": "filter",
      "path": "metadata.exam_relevant"
    }
  ]
}
```

7. Click **Create Search Index**
8. Wait for status to change from "Building" to "Active" (2-5 minutes)

**Troubleshooting**:
- If "Vector search not available" appears, upgrade to M10+ cluster
- Index name must be EXACTLY `course_materials_vector_index`
- Collection will be created automatically when you run setup scripts

---

## 3. Azure OpenAI Setup

### Step 1: Create Azure OpenAI Resource

1. Log in to [Azure Portal](https://portal.azure.com)
2. Click **Create a resource**
3. Search for **Azure OpenAI**
4. Click **Create**
5. Fill in details:
   - **Subscription**: Your Azure subscription
   - **Resource group**: Create new (e.g., `zeno-resources`)
   - **Region**: Choose available region (East US, West Europe, etc.)
   - **Name**: Unique name (e.g., `zeno-openai`)
   - **Pricing tier**: Standard S0
6. Click **Review + Create** → **Create**
7. Wait for deployment (1-2 minutes)

### Step 2: Deploy Models

1. Go to your Azure OpenAI resource
2. Click **Model deployments**
3. Click **Manage Deployments** (opens Azure OpenAI Studio)

**Deploy GPT-4:**
1. Click **Create new deployment**
2. Settings:
   - **Model**: `gpt-4` or `gpt-4-32k`
   - **Deployment name**: `gpt-4` ⚠️ Remember this!
   - **Tokens per Minute Rate Limit**: 10K (adjust as needed)
3. Click **Create**

**Deploy Embedding Model:**
1. Click **Create new deployment**  
2. Settings:
   - **Model**: `text-embedding-ada-002`
   - **Deployment name**: `text-embedding-ada-002` ⚠️ Remember this!
   - **Tokens per Minute Rate Limit**: 120K (adjust as needed)
3. Click **Create**

### Step 3: Get API Credentials

1. Go back to Azure Portal
2. Navigate to your Azure OpenAI resource
3. Click **Keys and Endpoint** in left sidebar
4. Copy and save:
   - **KEY 1** (your API key)
   - **Endpoint** (e.g., `https://zeno-openai.openai.azure.com/`)

---

## 4. Backend Installation

### Step 1: Clone Repository

```bash
git clone <your-repository-url>
cd Zeno/backend
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On Linux/Mac:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Expected output:
```
Successfully installed fastapi-0.112.0 uvicorn-0.30.0 ... openai-1.10.0
```

### Step 4: Configure Environment Variables

1. Copy example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` file with your credentials:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb+srv://zeno_user:YOUR_PASSWORD@zeno-cluster.abc123.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=zeno_db
MONGODB_COLLECTION=transcriptions
MONGODB_CONNECTION_TIMEOUT_MS=5000
MONGODB_SERVER_SELECTION_TIMEOUT_MS=5000
MONGODB_MAX_POOL_SIZE=10
MONGODB_MIN_POOL_SIZE=1

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://zeno-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-actual-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_CHAT_DEPLOYMENT=gpt-4

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Logging
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=development
```

### Step 5: Initialize Databases

**Setup RAG Collections:**
```bash
python -m api.rag.mongodb_setup
```

Expected output:
```
✓ Successfully connected to MongoDB
✓ Created collection: course_materials
✓ Created collection: generated_content  
✓ Created collection: semester_plans
✓ Created indexes...
✅ MongoDB setup completed successfully!
```

**Setup Learning System Collections:**
```bash
python -m api.learning.setup_indexes
```

Expected output:
```
Creating indexes for Learning Management System...
✓ student_cards indexes created
✓ practice_sessions indexes created
✓ question_bank indexes created
✓ skills indexes created
✓ student_skill_progress indexes created
✓ syllabus_alignment indexes created
✅ All Learning Management System indexes created successfully!
```

### Step 6: Start Backend Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO: Starting Zeno API with RAG capabilities...
INFO: ✓ MongoDB connection established successfully
INFO: RAG system status: healthy
INFO: ✓ Educational guardrails enabled
INFO: ✓ Learning Management System initialized
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
```

---

## 5. Frontend Installation

### Step 1: Navigate to Frontend

```bash
cd ../frontend  # From backend directory
```

### Step 2: Install Dependencies

```bash
npm install
```

### Step 3: Configure Environment

1. Copy example file:
```bash
cp .env.example .env.local
```

2. Edit `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 4: Start Development Server

```bash
npm run dev
```

Expected output:
```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
event - compiled successfully
```

---

## 6. System Verification

### Test 1: Backend Health Checks

```bash
# Main API health
curl http://localhost:8000/health

# Expected: {"ok": true, "service": "zeno-api"}

# RAG system health
curl http://localhost:8000/api/rag/health

# Expected: {"status": "healthy", "components": {...}}

# Learning system health
curl http://localhost:8000/api/learning/health

# Expected: {"status": "healthy", "service": "learning_management_system"}
```

### Test 2: MongoDB Connection

```bash
curl http://localhost:8000/db-ping

# Expected: {"mongo": "ok"}
```

### Test 3: OCR Document Processing

```bash
curl -X POST http://localhost:8000/api/rag/process-document \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "TEST_2024",
    "doc_type": "lecture_notes",
    "source_file": "test.pdf",
    "ocr_text": "Introduction to algorithms. Topics: sorting, searching.",
    "metadata": {"topic": "Algorithms"}
  }'

# Expected: {"status": "processing", "message": "Document test.pdf is being processed..."}
```

### Test 4: RAG Content Generation

```bash
# Wait a few seconds after processing document, then:
curl -X POST http://localhost:8000/api/rag/generate-quiz \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "TEST_2024",
    "topic": "Algorithms",
    "num_questions": 3,
    "difficulty": "medium"
  }'

# Expected: {"quiz_id": "...", "quiz": "[{...}]", "sources": [...]}
```

### Test 5: Learning System

```bash
# Get card statistics (should be 0 initially)
curl "http://localhost:8000/api/learning/cards/statistics?student_id=test_student&course_id=TEST_2024"

# Expected: {"total_cards": 0, "total_reviews": 0, ...}
```

### Test 6: Frontend Access

Open browser and navigate to:
- http://localhost:3000 - Frontend home page
- http://localhost:8000/docs - Backend API documentation (Swagger UI)

---

## 7. Troubleshooting

### Issue: "MongoDB connection failed"

**Symptoms**: Backend fails to start, error about MongoDB connection

**Solutions**:
1. Verify connection string in `.env`:
   ```bash
   echo $MONGODB_URI  # Should show your connection string
   ```

2. Check MongoDB Atlas Network Access:
   - Go to Atlas → Network Access
   - Ensure your IP is whitelisted

3. Test connection manually:
   ```bash
   mongosh "mongodb+srv://..."
   ```

4. Check MongoDB Atlas cluster is running (not paused)

### Issue: "Azure OpenAI unhealthy"

**Symptoms**: `/api/rag/health` shows Azure OpenAI as unhealthy

**Solutions**:
1. Verify credentials in `.env`:
   ```bash
   # Check endpoint
   echo $AZURE_OPENAI_ENDPOINT
   
   # Check key is set (don't print the actual key!)
   echo $AZURE_OPENAI_KEY | wc -c  # Should be 32-64 characters
   ```

2. Verify models are deployed:
   - Go to Azure OpenAI Studio
   - Check **Model deployments** tab
   - Both `gpt-4` and `text-embedding-ada-002` should show "Succeeded"

3. Check deployment names match exactly:
   ```bash
   echo $AZURE_CHAT_DEPLOYMENT  # Should be: gpt-4
   echo $AZURE_EMBEDDING_DEPLOYMENT  # Should be: text-embedding-ada-002
   ```

### Issue: "Vector index not found"

**Symptoms**: `/api/rag/health` shows `"vector_index": "not found"`

**Solutions**:
1. Check if index exists in Atlas:
   - Go to Atlas → Your Cluster → Search tab
   - Look for `course_materials_vector_index`

2. If missing, create it:
   - Follow [Step 5: Create Vector Search Index](#step-5-create-vector-search-index)
   - Wait for status to be "Active"

3. Verify index name is exact:
   - Must be `course_materials_vector_index`
   - Case-sensitive!

4. Check collection exists:
   - Go to Atlas → Collections
   - Should see `zeno_db.course_materials`

### Issue: "No relevant chunks retrieved"

**Symptoms**: Quiz generation returns empty or error

**Solutions**:
1. Process at least one document first:
   ```bash
   curl -X POST http://localhost:8000/api/rag/process-document ...
   ```

2. Verify documents in MongoDB:
   - Go to Atlas → Collections → `course_materials`
   - Should see documents with `content_vector` field

3. Check `course_id` matches:
   - Use same `course_id` for processing and generation

4. Wait for vector index to finish building:
   - Go to Atlas → Search → check status is "Active"

### Issue: "Import errors" or "Module not found"

**Symptoms**: Python import errors when starting server

**Solutions**:
1. Ensure virtual environment is activated:
   ```bash
   which python  # Should point to .venv/bin/python
   ```

2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

3. Check Python version:
   ```bash
   python --version  # Should be 3.10+
   ```

### Issue: "Port already in use"

**Symptoms**: Error when starting backend or frontend

**Solutions**:

For backend (port 8000):
```bash
# Find process using port 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>  # Mac/Linux
taskkill /PID <PID> /F  # Windows
```

For frontend (port 3000):
```bash
# Find and kill process
lsof -i :3000
kill -9 <PID>
```

### Issue: "CORS errors" in browser

**Symptoms**: Frontend can't connect to backend

**Solutions**:
1. Check `CORS_ORIGINS` in backend `.env`:
   ```bash
   CORS_ORIGINS=http://localhost:3000,http://localhost:3001
   ```

2. Restart backend server after changing `.env`

3. Clear browser cache and reload

### Issue: "Database indexes not created"

**Symptoms**: Slow queries or errors

**Solutions**:

Re-run setup scripts:
```bash
cd backend

# RAG system
python -m api.rag.mongodb_setup

# Learning system  
python -m api.learning.setup_indexes
```

Verify indexes in MongoDB Atlas:
- Go to Collections → Select collection → Indexes tab

---

## Next Steps

✅ Setup complete! Now you can:

1. **Upload documents** via OCR
2. **Generate questions** from course materials
3. **Create practice sessions** with spaced repetition
4. **Track student progress** with analytics

See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for comprehensive testing examples.

---

## Additional Resources

- **MongoDB Atlas Documentation**: https://www.mongodb.com/docs/atlas/
- **Azure OpenAI Documentation**: https://learn.microsoft.com/azure/ai-services/openai/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Next.js Documentation**: https://nextjs.org/docs

---

**Questions?** Check the troubleshooting section or review the server logs.

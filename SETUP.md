# Zeno Platform - Quick Setup

Get the platform running in 15 minutes.

---

## 1. Get API Keys

You need 2 services:
- **MongoDB Atlas** (free tier OK for dev)
- **Azure OpenAI** (requires Azure subscription)

**→ See [API_KEYS.md](./API_KEYS.md) for where to get and configure keys**

---

## 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your keys (see API_KEYS.md)

# Initialize databases
python -m api.rag.mongodb_setup
python -m api.learning.setup_indexes

# Start server
uvicorn main:app --reload
```

Server runs at: http://localhost:8000

---

## 3. Create Vector Search Index

**⚠️ CRITICAL STEP** - Do this in MongoDB Atlas UI:

1. Go to [MongoDB Atlas](https://cloud.mongodb.com) → Your Cluster → **Search** tab
2. Click **Create Search Index** → **JSON Editor**
3. Settings:
   - Database: `zeno_db`
   - Collection: `course_materials`
   - Index Name: `course_materials_vector_index`
4. Paste this JSON:

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
    }
  ]
}
```

5. Click **Create** → Wait for status: "Active" (2-5 min)

---

## 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure backend URL
cp .env.example .env.local
# Edit: NEXT_PUBLIC_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

Frontend runs at: http://localhost:3000

---

## 5. Verify Installation

```bash
# Check main API
curl http://localhost:8000/health

# Check RAG system
curl http://localhost:8000/api/rag/health

# Check Learning system
curl http://localhost:8000/api/learning/health
```

**Expected:** All show "healthy" status

---

## Troubleshooting

### MongoDB connection failed
- Check `.env` has correct `MONGODB_URI`
- Verify IP whitelist in Atlas Network Access
- Ensure password has no special characters (or URL encode)

### Azure OpenAI unhealthy
- Check `.env` has correct endpoint (must end with `/`)
- Verify API key is valid
- Ensure models are deployed in Azure OpenAI Studio

### Vector index not found
- Must create manually in Atlas UI (Step 3 above)
- Index name must be exactly: `course_materials_vector_index`
- Wait for status to be "Active"

### Import errors
- Activate virtual environment: `source .venv/bin/activate`
- Reinstall: `pip install -r requirements.txt`

---

## What's Next?

- **Test the system:** [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- **Learn the features:** [README.md](./README.md)
- **View API docs:** http://localhost:8000/docs

---

## Quick Links

- [API_KEYS.md](./API_KEYS.md) - Where to put API keys
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Test all features
- [README.md](./README.md) - Platform overview

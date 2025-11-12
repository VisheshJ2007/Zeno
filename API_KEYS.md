# API Keys Setup

## Where to Put API Keys

**File Location:** `backend/.env`

```bash
# Create the file (if it doesn't exist)
cd backend
cp .env.example .env

# Edit with your keys
nano .env  # or vim, code, etc.
```

---

## Required API Keys

### 1. MongoDB Atlas Connection String

**Where in .env:**
```bash
MONGODB_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

**How to get it:**
1. Go to [MongoDB Atlas](https://cloud.mongodb.com)
2. Click your cluster → "Connect" → "Connect your application"
3. Copy the connection string
4. Replace `<password>` with your actual password

**Format:** `mongodb+srv://username:password@cluster.mongodb.net/...`

---

### 2. Azure OpenAI Endpoint

**Where in .env:**
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
```

**How to get it:**
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Azure OpenAI resource
3. Click "Keys and Endpoint"
4. Copy the "Endpoint" value

**Format:** `https://RESOURCE-NAME.openai.azure.com/` (must end with `/`)

---

### 3. Azure OpenAI API Key

**Where in .env:**
```bash
AZURE_OPENAI_KEY=1234567890abcdef1234567890abcdef
```

**How to get it:**
1. Azure Portal → Your Azure OpenAI resource
2. Click "Keys and Endpoint"
3. Copy "KEY 1" or "KEY 2"

**Format:** 32-64 character alphanumeric string

---

### 4. Azure Deployment Names

**Where in .env:**
```bash
AZURE_CHAT_DEPLOYMENT=gpt-4
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

**How to get it:**
1. Azure OpenAI Studio → "Deployments" tab
2. Find your GPT-4 deployment name (you created this during setup)
3. Find your embedding deployment name

**Common names:**
- Chat: `gpt-4`, `gpt-4-32k`, `gpt-35-turbo`
- Embedding: `text-embedding-ada-002`

**IMPORTANT:** Use the exact deployment name you created, not the model name!

---

## Complete .env Example

```bash
# MongoDB Atlas
MONGODB_URI=mongodb+srv://zeno_user:MyPassword123@cluster0.abc123.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=zeno_db

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://my-openai-resource.openai.azure.com/
AZURE_OPENAI_KEY=abc123def456ghi789jkl012mno345pqr
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_CHAT_DEPLOYMENT=gpt-4
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Other settings (can leave as defaults)
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
LOG_LEVEL=INFO
ENVIRONMENT=development
```

---

## Testing Your Keys

```bash
# 1. Activate virtual environment
cd backend
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# 2. Start server
uvicorn main:app --reload

# 3. Test in another terminal
curl http://localhost:8000/api/rag/health

# Expected: All components show "healthy"
```

---

## Troubleshooting

### "MongoDB connection failed"
- ❌ Wrong: `mongodb://localhost:27017` (local, not Atlas)
- ✅ Right: `mongodb+srv://user:pass@cluster.mongodb.net/...`
- Check: IP whitelist in Atlas Network Access

### "Azure OpenAI unhealthy"
- ❌ Wrong: Missing trailing `/` in endpoint
- ✅ Right: `https://resource.openai.azure.com/`
- Check: Deployment names match exactly (case-sensitive)

### "Vector index not found"
- Not an API key issue
- Must create manually in MongoDB Atlas UI
- See SETUP_GUIDE.md Section 2, Step 5

---

## Security Notes

⚠️ **NEVER commit `.env` to git** (already in `.gitignore`)

✅ **Use different keys for:**
- Development (`.env`)
- Staging (`.env.staging`)
- Production (`.env.production`)

🔒 **Rotate keys regularly** via Azure Portal and MongoDB Atlas

---

**For full setup instructions, see:** [SETUP_GUIDE.md](./SETUP_GUIDE.md)

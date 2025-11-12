# Integrating AI-Enhanced OCR into Zeno

This guide explains how to integrate the AI-enhanced OCR system from this repository into the main Zeno application (https://github.com/VisheshJ2007/Zeno).

## Overview

This OCR system provides:
- **Azure Computer Vision Read API**: Handwriting-optimized OCR (5000 free requests/month)
- **Azure OpenAI GPT-4o**: AI post-processing to clean and format OCR text
- **RAG Context System**: Upload reference documents to improve AI accuracy
- **MongoDB Storage**: Persistent storage of OCR results and context
- **Modern Web Interface**: Dual-view (raw OCR vs AI-cleaned text)

---

## Architecture Components

### Backend Components
1. **Models**
   - `Document.js` - Stores OCR results with raw and AI-cleaned text
   - `ContextDocument.js` - Stores reference documents for RAG

2. **API Endpoints**
   - `POST /api/upload` - Upload images for OCR + AI processing
   - `GET /api/documents` - List all processed documents
   - `DELETE /api/documents/:id` - Delete a document
   - `POST /api/context` - Upload context documents
   - `GET /api/context` - List context documents
   - `DELETE /api/context/:id` - Delete context document

3. **Core Functions**
   - `runAzureVisionOCR()` - Performs OCR using Azure Computer Vision
   - `cleanOCRWithAI()` - Uses GPT-4o to clean and format text
   - `getRelevantContext()` - Retrieves context documents for RAG

### Frontend Components
- `index.html` - Two-tab interface (OCR Upload / Context Library)
- `app.js` - API integration, markdown rendering, file management
- `styles.css` - Modern, responsive styling

---

## Integration Options

### Option 1: Standalone Microservice (Recommended)

Keep the OCR system as a separate microservice that Zeno calls via API.

**Pros:**
- Isolated concerns, easier to maintain
- Can scale independently
- No impact on existing Zeno codebase

**Steps:**

1. **Deploy OCR service separately** (e.g., on port 5000)
2. **Call from Zeno backend:**

```javascript
// In your Zeno backend
const axios = require('axios');

async function processImageWithOCR(imagePath) {
  const formData = new FormData();
  formData.append('file', fs.createReadStream(imagePath));

  const response = await axios.post('http://localhost:5000/api/upload', formData, {
    headers: formData.getHeaders()
  });

  return response.data.document; // Returns { ocrText, aiCleanedText, confidence, etc. }
}
```

3. **Add CORS if calling from frontend:**
```javascript
// In OCR server.js
app.use(cors({
  origin: 'http://localhost:3000' // Your Zeno frontend URL
}));
```

---

### Option 2: Merge into Zeno Backend

Integrate the OCR functionality directly into Zeno's backend.

**Steps:**

#### 1. Copy Models
```bash
cp backend/models/Document.js /path/to/zeno/models/OCRDocument.js
cp backend/models/ContextDocument.js /path/to/zeno/models/ContextDocument.js
```

#### 2. Copy Core Functions
Add these functions to your Zeno backend (or create `services/ocr.js`):

```javascript
// services/ocr.js
const axios = require('axios');
const fs = require('fs');

async function runAzureVisionOCR(imagePath) {
  // Copy entire function from server.js lines 156-250
  // ...
}

async function cleanOCRWithAI(ocrText, contextText = '') {
  // Copy entire function from server.js lines 87-152
  // ...
}

async function getRelevantContext(ocrText, limit = 3) {
  // Copy entire function from server.js lines 59-84
  // ...
}

module.exports = { runAzureVisionOCR, cleanOCRWithAI, getRelevantContext };
```

#### 3. Add API Routes
```javascript
// routes/ocr.js
const express = require('express');
const router = express.Router();
const multer = require('multer');
const { runAzureVisionOCR, cleanOCRWithAI, getRelevantContext } = require('../services/ocr');
const OCRDocument = require('../models/OCRDocument');
const ContextDocument = require('../models/ContextDocument');

// Configure multer for file uploads
const upload = multer({
  storage: multer.diskStorage({
    destination: 'uploads/',
    filename: (req, file, cb) => {
      cb(null, Date.now() + '-' + Math.round(Math.random() * 1E9) + path.extname(file.originalname));
    }
  }),
  limits: { fileSize: 10 * 1024 * 1024 }
});

router.post('/upload', upload.single('file'), async (req, res) => {
  // Copy logic from server.js lines 254-301
});

router.get('/documents', async (req, res) => {
  // Copy logic from server.js lines 304-316
});

// ... other routes

module.exports = router;
```

#### 4. Register Routes in Zeno
```javascript
// In your main Zeno app.js or server.js
const ocrRoutes = require('./routes/ocr');
app.use('/api/ocr', ocrRoutes);
```

#### 5. Install Dependencies
```bash
cd /path/to/zeno
npm install axios multer
```

#### 6. Add Environment Variables
Add to Zeno's `.env`:
```
AZURE_VISION_KEY=your_key
AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

---

### Option 3: Frontend-Only Integration

If Zeno has its own backend, just integrate the frontend UI.

**Steps:**

1. **Copy Frontend Files:**
```bash
cp public/index.html /path/to/zeno/frontend/pages/ocr.html
cp public/app.js /path/to/zeno/frontend/js/ocr.js
cp public/styles.css /path/to/zeno/frontend/css/ocr.css
```

2. **Update API URL in app.js:**
```javascript
// Change this line in ocr.js
const API_URL = 'http://localhost:5000/api'; // Point to your OCR microservice
```

3. **Add Route in Zeno:**
```javascript
// If using React Router, Vue Router, etc.
<Route path="/ocr" component={OCRPage} />
```

---

## Environment Setup

### 1. Azure Computer Vision
1. Go to https://portal.azure.com
2. Create "Computer Vision" resource
3. Choose Free F0 tier (5000 requests/month)
4. Copy Key and Endpoint
5. Add to `.env`

See `AZURE_COMPUTER_VISION_SETUP.md` for detailed instructions.

### 2. Azure OpenAI
1. Go to https://portal.azure.com
2. Create "Azure OpenAI" resource
3. Deploy GPT-4o model
4. Copy Key, Endpoint, and Deployment name
5. Add to `.env`

### 3. MongoDB
```bash
# Install MongoDB locally or use MongoDB Atlas
# Update MONGODB_URI in .env
```

---

## Example Usage in Zeno

### Scenario 1: Process Uploaded Notes in Zeno

```javascript
// In Zeno's note creation endpoint
async function createNoteFromImage(req, res) {
  const imagePath = req.file.path;

  // Call OCR microservice
  const ocrResult = await processImageWithOCR(imagePath);

  // Save to Zeno's Note model with cleaned text
  const note = new Note({
    userId: req.user.id,
    title: extractTitle(ocrResult.aiCleanedText),
    content: ocrResult.aiCleanedText,
    rawOCR: ocrResult.ocrText,
    confidence: ocrResult.confidence,
    source: 'ocr-upload'
  });

  await note.save();
  res.json({ note });
}
```

### Scenario 2: Add Context Documents for Course Material

```javascript
// Upload course syllabus as context
const syllabusFile = await fetch('/api/context', {
  method: 'POST',
  body: formData, // Contains syllabus PDF
  headers: {
    'description': 'CS 101 Course Syllabus',
    'category': 'computer-science'
  }
});

// Now when uploading lecture notes, OCR will use syllabus context
// to better understand course-specific terminology
```

### Scenario 3: Batch Process Study Materials

```javascript
// Process multiple images at once
async function batchProcessStudyMaterials(imageFiles) {
  const results = await Promise.all(
    imageFiles.map(file => processImageWithOCR(file.path))
  );

  // Combine all cleaned text
  const studyGuide = results
    .map(r => r.aiCleanedText)
    .join('\n\n---\n\n');

  return studyGuide;
}
```

---

## API Reference

### POST /api/upload
Upload image for OCR processing.

**Request:**
```javascript
FormData {
  file: <image file>
}
```

**Response:**
```json
{
  "success": true,
  "document": {
    "id": "...",
    "originalName": "notes.jpg",
    "ocrText": "Raw OCR text...",
    "aiCleanedText": "# Cleaned Markdown Text...",
    "aiProcessed": true,
    "confidence": 85.5,
    "uploadDate": "2025-11-09T..."
  }
}
```

### POST /api/context
Upload context document for RAG.

**Request:**
```javascript
FormData {
  file: <text/pdf file>,
  description: "optional description",
  category: "optional category"
}
```

**Response:**
```json
{
  "success": true,
  "contextDocument": {
    "id": "...",
    "originalName": "syllabus.pdf",
    "description": "CS 101 Syllabus",
    "category": "computer-science",
    "uploadDate": "2025-11-09T..."
  }
}
```

---

## Performance Considerations

### Processing Time
- **OCR (Azure)**: 3-8 seconds for typical images
- **AI Cleaning (GPT-4o)**: 2-5 seconds
- **Total**: ~5-15 seconds per image

### Optimization Tips
1. **Process asynchronously**: Don't block user interactions
2. **Show progress indicators**: Users expect delays for AI processing
3. **Cache results**: Store in MongoDB, don't reprocess same images
4. **Batch when possible**: Process multiple images in parallel

### Rate Limits
- **Azure Computer Vision**: 5000 requests/month (free tier)
- **Azure OpenAI GPT-4o**: Varies by deployment (typically 20-60 requests/min)

---

## Testing

### Test OCR Endpoint
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@test-image.jpg"
```

### Test from Zeno Frontend
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:5000/api/upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('AI-Cleaned Text:', result.document.aiCleanedText);
```

---

## Deployment

### Deploy OCR Microservice

#### Option A: Same Server as Zeno
```bash
# Run on different port
cd ocr-test/backend
PORT=5001 npm start
```

#### Option B: Separate Server/Container
```dockerfile
# Dockerfile
FROM node:18
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5000
CMD ["node", "server.js"]
```

```bash
docker build -t ocr-service .
docker run -p 5000:5000 --env-file .env ocr-service
```

### Update Zeno to Call Service
```javascript
// In production, use environment variable
const OCR_SERVICE_URL = process.env.OCR_SERVICE_URL || 'http://localhost:5000';
```

---

## Security Considerations

1. **API Authentication**: Add authentication middleware if exposing publicly
2. **File Validation**: Already implemented (image-only for OCR, text-only for context)
3. **Rate Limiting**: Consider adding rate limits to prevent abuse
4. **Environment Variables**: Never commit `.env` to git (already in `.gitignore`)
5. **CORS**: Configure properly for production

---

## Troubleshooting

### "Cannot connect to backend"
- Ensure OCR service is running: `npm start` in `backend/`
- Check MongoDB is running: `mongod --version`
- Verify port is not in use: `lsof -i :5000`

### "Azure API not configured"
- Check `.env` file has correct Azure credentials
- Verify keys haven't expired in Azure Portal
- Test API keys independently

### "AI processing failed"
- Check Azure OpenAI quota in portal
- Verify GPT-4o deployment exists
- Check API version compatibility

---

## Next Steps

1. ✅ Choose integration option (Microservice recommended)
2. ✅ Set up Azure resources (Computer Vision + OpenAI)
3. ✅ Test OCR service independently
4. ✅ Integrate into Zeno codebase
5. ✅ Upload context documents relevant to your use case
6. ✅ Deploy and monitor

---

## Support & Resources

- **Azure Computer Vision Docs**: https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/
- **Azure OpenAI Docs**: https://learn.microsoft.com/en-us/azure/ai-services/openai/
- **This Repository**: https://github.com/triumviratesys/ocr-test
- **Zeno Repository**: https://github.com/VisheshJ2007/Zeno

---

## Cost Estimate

**Free Tier (Sufficient for most student use):**
- Azure Computer Vision: 5000 images/month = $0
- Azure OpenAI: Varies by quota, typically ~$5-10/month for moderate use
- MongoDB: Free tier sufficient

**Paid (High volume):**
- After 5000 images: $1/1000 transactions
- GPT-4o: ~$0.01-0.03 per OCR cleaning

For a student app like Zeno with ~100-500 users, free tier should be sufficient.

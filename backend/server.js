const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const FormData = require('form-data');
const axios = require('axios');
require('dotenv').config();

const Document = require('./models/Document');
const ContextDocument = require('./models/ContextDocument');

const app = express();

// Ensure uploads directory exists
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
  console.log('Created uploads directory');
}

// Middleware
app.use(cors());
app.use(express.json());
app.use('/uploads', express.static('uploads'));
app.use(express.static(path.join(__dirname, '../public')));

// MongoDB connection
mongoose.connect(process.env.MONGODB_URI)
  .then(() => console.log('Connected to MongoDB'))
  .catch(err => console.error('MongoDB connection error:', err));

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  }
});

const upload = multer({
  storage: storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif', 'image/bmp'];
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only image files are allowed.'));
    }
  }
});

// Configure multer for context documents (allows text files and PDFs)
const contextUpload = multer({
  storage: storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
  fileFilter: (req, file, cb) => {
    const allowedTypes = [
      'text/plain',
      'text/markdown',
      'text/csv',
      'application/json',
      'application/pdf'
    ];
    if (allowedTypes.includes(file.mimetype) || file.originalname.match(/\.(txt|md|json|csv|pdf)$/i)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only text, markdown, JSON, CSV, and PDF files are allowed.'));
    }
  }
});

// Helper function to retrieve relevant context documents for RAG
async function getRelevantContext(ocrText, limit = 3) {
  try {
    const contextDocs = await ContextDocument.find().sort({ uploadDate: -1 }).limit(limit);

    if (contextDocs.length === 0) {
      return '';
    }

    let contextText = '\n\n## Reference Context:\n';
    contextDocs.forEach((doc, index) => {
      contextText += `\n### Reference Document ${index + 1}: ${doc.originalName}\n`;
      if (doc.description) {
        contextText += `Description: ${doc.description}\n`;
      }
      if (doc.category) {
        contextText += `Category: ${doc.category}\n`;
      }
      contextText += `Content:\n${doc.content}\n`;
    });

    return contextText;
  } catch (error) {
    console.error('Error retrieving context:', error);
    return '';
  }
}

// Helper function to clean OCR text using Azure OpenAI
async function cleanOCRWithAI(ocrText, contextText = '') {
  try {
    const azureOpenAIKey = process.env.AZURE_OPENAI_API_KEY;
    const azureOpenAIEndpoint = process.env.AZURE_OPENAI_ENDPOINT;
    const azureOpenAIDeployment = process.env.AZURE_OPENAI_DEPLOYMENT || 'gpt-4o';
    const azureOpenAIVersion = process.env.AZURE_OPENAI_API_VERSION || '2024-08-01-preview';

    if (!azureOpenAIKey || !azureOpenAIEndpoint) {
      console.log('Azure OpenAI not configured, skipping AI post-processing');
      return {
        success: false,
        cleanedText: ocrText,
        error: 'Azure OpenAI not configured'
      };
    }

    const apiUrl = `${azureOpenAIEndpoint}/openai/deployments/${azureOpenAIDeployment}/chat/completions?api-version=${azureOpenAIVersion}`;

    const systemPrompt = `You are an AI assistant that corrects and reformats OCR text. Your tasks:
1. Fix spelling errors and typos from OCR misreading
2. Correct word spacing issues (e.g., "wend-to-end" → "end-to-end")
3. Fix capitalization and punctuation
4. Preserve the original structure and meaning
5. Use the reference context (if provided) to understand domain-specific terminology
6. Format the output in clear markdown with proper headings and lists

IMPORTANT: Only fix obvious OCR errors. Do not add new information or change the meaning.`;

    const userPrompt = `Please clean and reformat this OCR text:\n\n${ocrText}${contextText}`;

    const response = await axios.post(
      apiUrl,
      {
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt }
        ],
        temperature: 0.3,
        max_tokens: 2000
      },
      {
        headers: {
          'api-key': azureOpenAIKey,
          'Content-Type': 'application/json'
        }
      }
    );

    const cleanedText = response.data.choices[0].message.content;

    return {
      success: true,
      cleanedText: cleanedText,
      model: azureOpenAIDeployment,
      error: null
    };

  } catch (error) {
    console.error('Azure OpenAI error:', error.response?.data || error.message);
    return {
      success: false,
      cleanedText: ocrText,
      error: error.message
    };
  }
}

// Routes

// Helper function to run OCR using Azure Computer Vision Read API
async function runAzureVisionOCR(imagePath) {
  try {
    const azureKey = process.env.AZURE_VISION_KEY;
    const azureEndpoint = process.env.AZURE_VISION_ENDPOINT;

    if (!azureKey || !azureEndpoint) {
      throw new Error('Azure Vision API key or endpoint not configured. Please set AZURE_VISION_KEY and AZURE_VISION_ENDPOINT in .env');
    }

    // Read the image file
    const imageBuffer = fs.readFileSync(imagePath);

    // Step 1: Submit image for analysis
    const analyzeUrl = `${azureEndpoint}/vision/v3.2/read/analyze`;

    const submitResponse = await axios.post(analyzeUrl, imageBuffer, {
      headers: {
        'Ocp-Apim-Subscription-Key': azureKey,
        'Content-Type': 'application/octet-stream'
      },
      maxContentLength: Infinity,
      maxBodyLength: Infinity
    });

    // Get the operation location from the response headers
    const operationLocation = submitResponse.headers['operation-location'];

    if (!operationLocation) {
      throw new Error('No operation location returned from Azure');
    }

    // Step 2: Poll for results
    let result;
    let attempts = 0;
    const maxAttempts = 30; // 30 seconds max wait

    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second

      const resultResponse = await axios.get(operationLocation, {
        headers: {
          'Ocp-Apim-Subscription-Key': azureKey
        }
      });

      result = resultResponse.data;

      if (result.status === 'succeeded') {
        break;
      } else if (result.status === 'failed') {
        throw new Error('Azure OCR processing failed');
      }

      attempts++;
    }

    if (result.status !== 'succeeded') {
      throw new Error('Azure OCR processing timed out');
    }

    // Extract text and confidence from results
    let fullText = '';
    let totalConfidence = 0;
    let lineCount = 0;

    if (result.analyzeResult && result.analyzeResult.readResults) {
      result.analyzeResult.readResults.forEach(page => {
        page.lines?.forEach(line => {
          fullText += line.text + '\n';
          // Azure provides confidence at word level
          if (line.words) {
            line.words.forEach(word => {
              if (word.confidence !== undefined) {
                totalConfidence += word.confidence;
                lineCount++;
              }
            });
          }
        });
      });
    }

    const avgConfidence = lineCount > 0 ? (totalConfidence / lineCount) * 100 : 85.0;

    return {
      success: true,
      text: fullText.trim(),
      confidence: Math.round(avgConfidence * 100) / 100,
      error: null
    };

  } catch (error) {
    console.error('Azure Vision API error:', error.response?.data || error.message);
    throw new Error(`OCR processing failed: ${error.response?.data?.error?.message || error.message}`);
  }
}

// Upload and process file with OCR
app.post('/api/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    console.log('Processing OCR for:', req.file.originalname);

    // Perform OCR on the uploaded file using Azure Computer Vision Read API
    const result = await runAzureVisionOCR(req.file.path);

    console.log('OCR completed with confidence:', result.confidence + '%');

    // Get relevant context for RAG
    const contextText = await getRelevantContext(result.text);

    // Clean OCR text with AI
    console.log('Running AI post-processing...');
    const aiResult = await cleanOCRWithAI(result.text, contextText);

    if (aiResult.success) {
      console.log('AI post-processing completed successfully');
    } else {
      console.log('AI post-processing skipped or failed:', aiResult.error);
    }

    // Save document metadata and OCR results to MongoDB
    const document = new Document({
      filename: req.file.filename,
      originalName: req.file.originalname,
      filePath: req.file.path,
      mimeType: req.file.mimetype,
      size: req.file.size,
      ocrText: result.text,
      ocrConfidence: result.confidence,
      aiCleanedText: aiResult.cleanedText,
      aiProcessed: aiResult.success,
      aiModel: aiResult.model || ''
    });

    await document.save();

    res.json({
      success: true,
      document: {
        id: document._id,
        originalName: document.originalName,
        ocrText: document.ocrText,
        aiCleanedText: document.aiCleanedText,
        aiProcessed: document.aiProcessed,
        confidence: document.ocrConfidence,
        uploadDate: document.uploadDate
      }
    });

  } catch (error) {
    console.error('Upload error:', error);

    // Clean up uploaded file if processing failed
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }

    res.status(500).json({ error: 'Error processing file: ' + error.message });
  }
});

// Get all documents
app.get('/api/documents', async (req, res) => {
  try {
    const documents = await Document.find().sort({ uploadDate: -1 });
    res.json(documents);
  } catch (error) {
    console.error('Error fetching documents:', error);
    res.status(500).json({ error: 'Error fetching documents' });
  }
});

// Get single document by ID
app.get('/api/documents/:id', async (req, res) => {
  try {
    const document = await Document.findById(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    res.json(document);
  } catch (error) {
    console.error('Error fetching document:', error);
    res.status(500).json({ error: 'Error fetching document' });
  }
});

// Delete document
app.delete('/api/documents/:id', async (req, res) => {
  try {
    const document = await Document.findById(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }

    // Delete file from filesystem
    if (fs.existsSync(document.filePath)) {
      fs.unlinkSync(document.filePath);
    }

    // Delete from database
    await Document.findByIdAndDelete(req.params.id);

    res.json({ success: true, message: 'Document deleted' });
  } catch (error) {
    console.error('Error deleting document:', error);
    res.status(500).json({ error: 'Error deleting document' });
  }
});

// Upload context document
app.post('/api/context', contextUpload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    console.log('Processing context document:', req.file.originalname);

    // Read file content (support text and PDF files)
    let content = '';
    const ext = path.extname(req.file.originalname).toLowerCase();

    if (['.txt', '.md', '.json', '.csv'].includes(ext)) {
      content = fs.readFileSync(req.file.path, 'utf-8');
    } else if (ext === '.pdf') {
      // For PDFs, you could use pdf-parse library, but for now just store the file path
      content = `[PDF file - path: ${req.file.path}]`;
    } else {
      content = `[File content - type: ${req.file.mimetype}]`;
    }

    // Get description and category from request body
    const description = req.body.description || '';
    const category = req.body.category || 'general';

    // Save context document to MongoDB
    const contextDoc = new ContextDocument({
      filename: req.file.filename,
      originalName: req.file.originalname,
      filePath: req.file.path,
      mimeType: req.file.mimetype,
      size: req.file.size,
      content: content,
      description: description,
      category: category
    });

    await contextDoc.save();

    res.json({
      success: true,
      contextDocument: {
        id: contextDoc._id,
        originalName: contextDoc.originalName,
        description: contextDoc.description,
        category: contextDoc.category,
        uploadDate: contextDoc.uploadDate
      }
    });

  } catch (error) {
    console.error('Context upload error:', error);

    // Clean up uploaded file if processing failed
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }

    res.status(500).json({ error: 'Error processing context file: ' + error.message });
  }
});

// Get all context documents
app.get('/api/context', async (req, res) => {
  try {
    const contextDocs = await ContextDocument.find().sort({ uploadDate: -1 });
    res.json(contextDocs);
  } catch (error) {
    console.error('Error fetching context documents:', error);
    res.status(500).json({ error: 'Error fetching context documents' });
  }
});

// Delete context document
app.delete('/api/context/:id', async (req, res) => {
  try {
    const contextDoc = await ContextDocument.findById(req.params.id);
    if (!contextDoc) {
      return res.status(404).json({ error: 'Context document not found' });
    }

    // Delete file from filesystem
    if (fs.existsSync(contextDoc.filePath)) {
      fs.unlinkSync(contextDoc.filePath);
    }

    // Delete from database
    await ContextDocument.findByIdAndDelete(req.params.id);

    res.json({ success: true, message: 'Context document deleted' });
  } catch (error) {
    console.error('Error deleting context document:', error);
    res.status(500).json({ error: 'Error deleting context document' });
  }
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

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
const NoteSet = require('./models/NoteSet');

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

// Helper function to analyze layout with Azure Document Intelligence
async function analyzeDocumentLayout(imagePath) {
  try {
    const azureKey = process.env.AZURE_VISION_KEY;
    const azureEndpoint = process.env.AZURE_VISION_ENDPOINT;

    if (!azureKey || !azureEndpoint) {
      console.log('Azure credentials not configured for Document Intelligence');
      return { success: false, layoutInfo: null };
    }

    const imageBuffer = fs.readFileSync(imagePath);

    // Use Document Intelligence prebuilt-layout model
    const analyzeUrl = `${azureEndpoint}/formrecognizer/documentModels/prebuilt-layout:analyze?api-version=2023-07-31`;

    const submitResponse = await axios.post(analyzeUrl, imageBuffer, {
      headers: {
        'Ocp-Apim-Subscription-Key': azureKey,
        'Content-Type': 'application/octet-stream'
      },
      maxContentLength: Infinity,
      maxBodyLength: Infinity
    });

    const operationLocation = submitResponse.headers['operation-location'];

    // Poll for results
    let result;
    let attempts = 0;
    const maxAttempts = 30;

    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 1000));

      const resultResponse = await axios.get(operationLocation, {
        headers: { 'Ocp-Apim-Subscription-Key': azureKey }
      });

      result = resultResponse.data;
      if (result.status === 'succeeded') break;
      if (result.status === 'failed') {
        console.log('Document Intelligence analysis failed');
        return { success: false, layoutInfo: null };
      }
      attempts++;
    }

    return {
      success: true,
      layoutInfo: result.analyzeResult
    };
  } catch (error) {
    console.log('Document Intelligence not available, skipping layout analysis:', error.message);
    return { success: false, layoutInfo: null };
  }
}

// Helper function to clean OCR text using Azure OpenAI with Vision
async function cleanOCRWithAI(ocrText, imagePath, contextText = '') {
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

    // Read and encode image as base64
    const imageBuffer = fs.readFileSync(imagePath);
    const base64Image = imageBuffer.toString('base64');
    const mimeType = imagePath.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg';

    const systemPrompt = `You are an AI assistant that analyzes images with text and structure. Your tasks:
1. Look at the IMAGE to understand the VISUAL STRUCTURE (arrows, boxes, diagrams, indentation, layout)
2. Fix ONLY obvious spelling errors and typos from OCR
3. Interpret arrows (→, ↓, ←, ↑) and connections between text elements
4. Create proper hierarchical structure with markdown indentation based on visual relationships
5. Preserve tables, lists, and sectioning you see in the image
6. Use the reference context (if provided) to understand domain-specific terminology

CRITICAL RULES FOR STRUCTURE:
- If you see arrows connecting concepts, represent them as indented bullet points or numbered lists
- If text boxes are connected by arrows, show the flow with proper nesting
- Respect visual hierarchy (main points vs sub-points based on size, position, indentation)
- Preserve tables exactly as they appear visually
- Use markdown formatting: # for headers, - for bullets, proper indentation for sub-items

CRITICAL RULES FOR TEXT:
- Change as FEW words as possible - prefer keeping original wording
- Do NOT add new information not present in the image
- If you're unsure whether something is an OCR error, keep it as-is`;

    const userPrompt = `Analyze this image and the OCR text below. Create properly structured markdown that reflects the VISUAL layout, arrows, and hierarchical relationships you see in the image.

OCR Text for reference:
${ocrText}
${contextText}

Please provide the cleaned, properly structured output in markdown format.`;

    const response = await axios.post(
      apiUrl,
      {
        messages: [
          { role: 'system', content: systemPrompt },
          {
            role: 'user',
            content: [
              {
                type: 'text',
                text: userPrompt
              },
              {
                type: 'image_url',
                image_url: {
                  url: `data:${mimeType};base64,${base64Image}`
                }
              }
            ]
          }
        ],
        temperature: 0.1,
        max_tokens: 3000
      },
      {
        headers: {
          'api-key': azureOpenAIKey,
          'Content-Type': 'application/json'
        }
      }
    );

    let cleanedText = response.data.choices[0].message.content;

    // Remove markdown code fences if present
    cleanedText = cleanedText.replace(/^```markdown\n/gm, '').replace(/^```\n/gm, '').replace(/\n```$/gm, '');

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

    // Run OCR and layout analysis in parallel
    console.log('Starting OCR and layout analysis...');
    const [result, layoutResult] = await Promise.all([
      runAzureVisionOCR(req.file.path),
      analyzeDocumentLayout(req.file.path)
    ]);

    console.log('OCR completed with confidence:', result.confidence + '%');
    if (layoutResult.success) {
      console.log('Document Intelligence layout analysis completed');
    } else {
      console.log('Document Intelligence skipped (using basic OCR only)');
    }

    // Get relevant context for RAG
    const contextText = await getRelevantContext(result.text);

    // Clean OCR text with AI Vision (analyzes image for structure, arrows, etc.)
    console.log('Running AI post-processing with vision analysis...');
    const aiResult = await cleanOCRWithAI(result.text, req.file.path, contextText);

    if (aiResult.success) {
      console.log('AI post-processing with vision analysis completed successfully');
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

// Batch upload and process multiple files with OCR
app.post('/api/upload-batch', upload.array('files', 20), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ error: 'No files uploaded' });
    }

    const noteSetName = req.body.noteSetName || `Note Set ${new Date().toLocaleDateString()}`;
    console.log(`Processing batch upload of ${req.files.length} files for note set: ${noteSetName}`);

    const processedDocuments = [];
    const errors = [];

    // Process each file
    for (let i = 0; i < req.files.length; i++) {
      const file = req.files[i];
      try {
        console.log(`Processing file ${i + 1}/${req.files.length}: ${file.originalname}`);

        // Run OCR and layout analysis in parallel
        const [result, layoutResult] = await Promise.all([
          runAzureVisionOCR(file.path),
          analyzeDocumentLayout(file.path)
        ]);

        console.log(`OCR completed for ${file.originalname} with confidence: ${result.confidence}%`);

        // Get relevant context for RAG
        const contextText = await getRelevantContext(result.text);

        // Clean OCR text with AI Vision
        const aiResult = await cleanOCRWithAI(result.text, file.path, contextText);

        // Save document
        const document = new Document({
          filename: file.filename,
          originalName: file.originalname,
          filePath: file.path,
          mimeType: file.mimetype,
          size: file.size,
          ocrText: result.text,
          ocrConfidence: result.confidence,
          aiCleanedText: aiResult.cleanedText,
          aiProcessed: aiResult.success,
          aiModel: aiResult.model || ''
        });

        await document.save();
        processedDocuments.push({
          documentId: document._id,
          order: i
        });

        console.log(`Successfully processed ${file.originalname}`);
      } catch (error) {
        console.error(`Error processing ${file.originalname}:`, error);
        errors.push({
          filename: file.originalname,
          error: error.message
        });

        // Clean up file on error
        if (fs.existsSync(file.path)) {
          fs.unlinkSync(file.path);
        }
      }
    }

    // Create note set if at least one document was processed
    let noteSet = null;
    if (processedDocuments.length > 0) {
      noteSet = new NoteSet({
        name: noteSetName,
        documents: processedDocuments
      });
      await noteSet.save();
      console.log(`Created note set: ${noteSetName} with ${processedDocuments.length} documents`);
    }

    res.json({
      success: true,
      noteSet: noteSet ? {
        id: noteSet._id,
        name: noteSet.name,
        documentCount: processedDocuments.length,
        createdDate: noteSet.createdDate
      } : null,
      processedCount: processedDocuments.length,
      errorCount: errors.length,
      errors: errors
    });

  } catch (error) {
    console.error('Batch upload error:', error);

    // Clean up uploaded files if processing failed
    if (req.files) {
      req.files.forEach(file => {
        if (fs.existsSync(file.path)) {
          fs.unlinkSync(file.path);
        }
      });
    }

    res.status(500).json({ error: 'Error processing batch upload: ' + error.message });
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

// Update document text
app.put('/api/documents/:id', async (req, res) => {
  try {
    const { ocrText, aiCleanedText } = req.body;

    const document = await Document.findById(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }

    // Update fields if provided
    if (ocrText !== undefined) {
      document.ocrText = ocrText;
    }
    if (aiCleanedText !== undefined) {
      document.aiCleanedText = aiCleanedText;
    }

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
    console.error('Error updating document:', error);
    res.status(500).json({ error: 'Error updating document' });
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

// ==== Note Set Endpoints ====

// Get all note sets
app.get('/api/notesets', async (req, res) => {
  try {
    const noteSets = await NoteSet.find()
      .populate('documents.documentId')
      .sort({ updatedDate: -1 });
    res.json(noteSets);
  } catch (error) {
    console.error('Error fetching note sets:', error);
    res.status(500).json({ error: 'Error fetching note sets' });
  }
});

// Get single note set by ID
app.get('/api/notesets/:id', async (req, res) => {
  try {
    const noteSet = await NoteSet.findById(req.params.id)
      .populate('documents.documentId');
    if (!noteSet) {
      return res.status(404).json({ error: 'Note set not found' });
    }
    res.json(noteSet);
  } catch (error) {
    console.error('Error fetching note set:', error);
    res.status(500).json({ error: 'Error fetching note set' });
  }
});

// Create new note set (from existing documents)
app.post('/api/notesets', async (req, res) => {
  try {
    const { name, documentIds } = req.body;

    if (!name || !documentIds || !Array.isArray(documentIds) || documentIds.length === 0) {
      return res.status(400).json({ error: 'Name and documentIds array required' });
    }

    const documents = documentIds.map((id, index) => ({
      documentId: id,
      order: index
    }));

    const noteSet = new NoteSet({
      name,
      documents
    });

    await noteSet.save();

    const populatedNoteSet = await NoteSet.findById(noteSet._id)
      .populate('documents.documentId');

    res.json({
      success: true,
      noteSet: populatedNoteSet
    });
  } catch (error) {
    console.error('Error creating note set:', error);
    res.status(500).json({ error: 'Error creating note set' });
  }
});

// Update note set (rename or reorder documents)
app.put('/api/notesets/:id', async (req, res) => {
  try {
    const { name, documents } = req.body;

    const noteSet = await NoteSet.findById(req.params.id);
    if (!noteSet) {
      return res.status(404).json({ error: 'Note set not found' });
    }

    if (name !== undefined) {
      noteSet.name = name;
    }

    if (documents !== undefined && Array.isArray(documents)) {
      noteSet.documents = documents;
    }

    await noteSet.save();

    const populatedNoteSet = await NoteSet.findById(noteSet._id)
      .populate('documents.documentId');

    res.json({
      success: true,
      noteSet: populatedNoteSet
    });
  } catch (error) {
    console.error('Error updating note set:', error);
    res.status(500).json({ error: 'Error updating note set' });
  }
});

// Add document to note set
app.post('/api/notesets/:id/documents', async (req, res) => {
  try {
    const { documentId } = req.body;

    if (!documentId) {
      return res.status(400).json({ error: 'documentId required' });
    }

    const noteSet = await NoteSet.findById(req.params.id);
    if (!noteSet) {
      return res.status(404).json({ error: 'Note set not found' });
    }

    // Check if document already exists in set
    const exists = noteSet.documents.some(doc => doc.documentId.toString() === documentId);
    if (exists) {
      return res.status(400).json({ error: 'Document already in note set' });
    }

    // Add document with order based on current length
    noteSet.documents.push({
      documentId,
      order: noteSet.documents.length
    });

    await noteSet.save();

    const populatedNoteSet = await NoteSet.findById(noteSet._id)
      .populate('documents.documentId');

    res.json({
      success: true,
      noteSet: populatedNoteSet
    });
  } catch (error) {
    console.error('Error adding document to note set:', error);
    res.status(500).json({ error: 'Error adding document to note set' });
  }
});

// Remove document from note set
app.delete('/api/notesets/:id/documents/:documentId', async (req, res) => {
  try {
    const noteSet = await NoteSet.findById(req.params.id);
    if (!noteSet) {
      return res.status(404).json({ error: 'Note set not found' });
    }

    // Filter out the document
    noteSet.documents = noteSet.documents.filter(
      doc => doc.documentId.toString() !== req.params.documentId
    );

    // Reorder remaining documents
    noteSet.documents.forEach((doc, index) => {
      doc.order = index;
    });

    await noteSet.save();

    const populatedNoteSet = await NoteSet.findById(noteSet._id)
      .populate('documents.documentId');

    res.json({
      success: true,
      noteSet: populatedNoteSet
    });
  } catch (error) {
    console.error('Error removing document from note set:', error);
    res.status(500).json({ error: 'Error removing document from note set' });
  }
});

// Delete note set
app.delete('/api/notesets/:id', async (req, res) => {
  try {
    const noteSet = await NoteSet.findByIdAndDelete(req.params.id);
    if (!noteSet) {
      return res.status(404).json({ error: 'Note set not found' });
    }

    res.json({ success: true, message: 'Note set deleted' });
  } catch (error) {
    console.error('Error deleting note set:', error);
    res.status(500).json({ error: 'Error deleting note set' });
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

// Serve uploaded images
app.get('/api/documents/:id/image', async (req, res) => {
  try {
    const document = await Document.findById(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }

    if (!fs.existsSync(document.filePath)) {
      return res.status(404).json({ error: 'Image file not found' });
    }

    res.sendFile(path.resolve(document.filePath));
  } catch (error) {
    console.error('Error serving image:', error);
    res.status(500).json({ error: 'Error serving image' });
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

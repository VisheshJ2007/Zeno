# OCR Backend with Google Cloud Vision API

This backend uses **Google Cloud Vision API**, Google's state-of-the-art OCR service, to extract text from images with industry-leading accuracy.

## Features

- **SOTA OCR**: Google Cloud Vision provides industry-leading accuracy
- **Large File Support**: Handles images up to **20MB** (vs 1MB for free alternatives)
- **No Heavy Dependencies**: No PyTorch or large ML models to download
- **Fast Processing**: Cloud-based processing with low latency
- **Multi-language support**: Supports 100+ languages (currently configured for English)
- **Real Confidence Scores**: Actual word-level confidence metrics
- **Generous Free Tier**: 1000 requests/month free forever
- **RESTful API**: Simple HTTP API for file uploads and OCR processing
- **MongoDB storage**: Stores document metadata and OCR results

## Requirements

### Node.js Dependencies
- Express.js
- Mongoose (MongoDB ODM)
- Multer (file uploads)
- Axios (HTTP client)
- Form-data (multipart form handling)
- CORS
- dotenv

### No Python Required!
This implementation uses a cloud API, so no Python dependencies or large downloads are needed.

## Installation

### 1. Install Node.js Dependencies
```bash
npm install
```

### 2. Get Google Cloud Vision API Key (5 minutes)
**IMPORTANT**: You need a free Google Cloud Vision API key to use this OCR service.

📖 **See `GOOGLE_VISION_SETUP.md` for detailed step-by-step instructions**

Quick steps:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new project
3. Enable "Cloud Vision API"
4. Create an API key
5. Copy the key

### 3. Configure Environment Variables
Create/update `.env` file in the backend directory:
```
MONGODB_URI=mongodb://localhost:27017/ocr-database
PORT=5000
GOOGLE_VISION_API_KEY=your_actual_api_key_here
```

**Free Tier**: 1000 requests/month, up to 20MB per image

### 4. Start MongoDB
Ensure MongoDB is running on your system.

### 5. Start the Server
```bash
npm start
```

For development with auto-reload:
```bash
npm run dev
```

## API Endpoints

### Upload and Process Image
**POST** `/api/upload`
- Upload an image file for OCR processing
- Accepts: JPEG, PNG, JPG, GIF, BMP
- Max file size: 10MB
- Returns: Document metadata, extracted text, and confidence score

### Get All Documents
**GET** `/api/documents`
- Returns list of all processed documents

### Get Single Document
**GET** `/api/documents/:id`
- Returns specific document by ID

### Delete Document
**DELETE** `/api/documents/:id`
- Deletes document and associated file

### Health Check
**GET** `/api/health`
- Returns server status

## OCR Processing

The backend uses **Google Cloud Vision API** for text extraction. The service is cloud-based and provides:

1. **DOCUMENT_TEXT_DETECTION**: Optimized for document OCR with superior accuracy
2. **Automatic Orientation Detection**: Handles rotated and skewed images
3. **Word-level Confidence Scores**: Real confidence metrics for each detected word
4. **Multi-language Support**: 100+ languages with automatic detection
5. **Large File Support**: Up to 20MB images (vs 1MB for free alternatives)

### Advantages of Google Cloud Vision API:
1. **Industry-Leading Accuracy**: Used by Google internally for production services
2. **No Installation**: Zero dependencies beyond Node.js packages
3. **Fast Setup**: No model downloads or training
4. **Scalable**: Google's infrastructure handles any load
5. **Multi-format**: Supports JPG, PNG, GIF, BMP, WebP, RAW, ICO, PDF, TIFF
6. **Always Updated**: Benefit from Google's continuous ML improvements
7. **Generous Free Tier**: 1000 requests/month free forever

## Configuration

### Changing OCR Language
Edit `server.js` in the `runGoogleVisionOCR` function:
```javascript
imageContext: {
  languageHints: ['en', 'es'] // Add multiple languages for better detection
}
```

Supported language codes: en, es, fr, de, ja, zh, ar, hi, etc.

### API Key Setup
See `GOOGLE_VISION_SETUP.md` for detailed instructions on getting your free API key.

### Free Tier Limits
Google Cloud Vision free tier:
- **1000 requests per month** - FREE forever
- **After 1000**: $1.50 per 1000 requests
- **Max 20MB per image** (4MB for base64)
- **No rate limits** for free tier
- **No credit card required** for free tier

## Troubleshooting

### "API key not valid" Error
- Make sure you created a Google Cloud Vision API key
- Verify you enabled the Cloud Vision API in your project
- Check that the key is correctly added to `.env` file
- Restart the server after updating `.env`
- See `GOOGLE_VISION_SETUP.md` for step-by-step instructions

### "Quota exceeded" Error
- You've used your 1000 free requests this month
- Check usage at: https://console.cloud.google.com/apis/dashboard
- Either wait until next month or upgrade to paid tier

### Image Format Issues
Supported formats: JPG, PNG, GIF, BMP, WebP, RAW, ICO, PDF, TIFF
If images fail to process:
- Check file size (max 20MB for direct upload, 4MB for base64)
- Ensure the image is not corrupted
- Try converting to PNG or JPEG for best results

### Connection Issues
If the API is unreachable:
- Check your internet connection
- Verify the API endpoint is correct
- Check Google Cloud status: https://status.cloud.google.com/

## Comparison: Google Cloud Vision vs Alternatives

| Feature | Google Vision API | OCR.space | Tesseract.js |
|---------|------------------|-----------|--------------|
| Accuracy | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Max File Size | **20MB** | 1MB | No limit |
| Setup Time | 5 minutes | 30 seconds | 5 minutes |
| Dependencies | Minimal | Minimal | Heavy (WebAssembly) |
| Processing Speed | Very Fast | Fast | Slower (local) |
| Languages | 100+ | 100+ | 100+ |
| Offline | ❌ | ❌ | ✅ |
| Free Tier | 1000/month | 25000/month (1MB limit) | Unlimited |
| Confidence Scores | Real word-level | Estimated | Yes |
| Best For | **Production** | Hobby projects | Offline apps |

## License

This project uses open-source components. Please refer to individual package licenses.

const mongoose = require('mongoose');

const documentSchema = new mongoose.Schema({
  filename: {
    type: String,
    required: true
  },
  originalName: {
    type: String,
    required: true
  },
  filePath: {
    type: String,
    required: true
  },
  mimeType: {
    type: String,
    required: true
  },
  size: {
    type: Number,
    required: true
  },
  ocrText: {
    type: String,
    default: ''
  },
  ocrConfidence: {
    type: Number,
    default: 0
  },
  aiCleanedText: {
    type: String,
    default: ''
  },
  aiProcessed: {
    type: Boolean,
    default: false
  },
  aiModel: {
    type: String,
    default: ''
  },
  uploadDate: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('Document', documentSchema);

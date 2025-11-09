const mongoose = require('mongoose');

const noteSetSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    trim: true
  },
  documents: [{
    documentId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Document',
      required: true
    },
    order: {
      type: Number,
      required: true,
      default: 0
    }
  }],
  createdDate: {
    type: Date,
    default: Date.now
  },
  updatedDate: {
    type: Date,
    default: Date.now
  }
});

// Update the updatedDate before saving
noteSetSchema.pre('save', function(next) {
  this.updatedDate = Date.now();
  next();
});

const NoteSet = mongoose.model('NoteSet', noteSetSchema);

module.exports = NoteSet;

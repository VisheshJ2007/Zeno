// Small test script to verify MongoDB connection using MONGO_URI from .env
// Run: node check_mongo.js

require('dotenv').config();
const mongoose = require('mongoose');

const mongoUri = process.env.MONGO_URI || process.env.MONGODB_URI;
if (!mongoUri) {
  console.error('No MONGO_URI or MONGODB_URI found in environment. Check backend/.env');
  process.exit(1);
}

console.log('Testing MongoDB connection to:', mongoUri.replace(/(mongodb\+srv:\/\/)[^@]*@/, '$1***:***@'));

mongoose.connect(mongoUri, { connectTimeoutMS: 10000 }).then(() => {
  console.log('Connected to MongoDB successfully');
  return mongoose.connection.close();
}).catch(err => {
  console.error('MongoDB connection failed:');
  console.error(err && err.message ? err.message : err);
  process.exit(1);
});

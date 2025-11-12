// Import required modules
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');

// Create Express app
const app = express();
app.use(cors()); // Allow frontend to connect

// Create HTTP server
const server = http.createServer(app);

// Setup Socket.IO for real-time communication
const io = socketIo(server, {
  cors: {
    origin: "http://localhost:3000", // Your React app's address
    methods: ["GET", "POST"]
  }
});

// Store shared code
let sharedCode = "// Welcome to CodePulse! Start coding together...\n";

// Handle new connections
io.on('connection', (socket) => {
  console.log('User connected:', socket.id);
  
  // Send current code to new user
  socket.emit('code-update', sharedCode);
  
  // Listen for code changes
  socket.on('code-change', (newCode) => {
    sharedCode = newCode;
    // Send to all other users
    socket.broadcast.emit('code-update', newCode);
  });

  socket.on('disconnect', () => {
    console.log('User disconnected:', socket.id);
  });
});

// Start server
const PORT = 3001;
server.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
});
/**
 * AURA Frontend Server
 * Express server serving the frontend application
 */

const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static('public'));

// Serve main page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Start server
app.listen(PORT, () => {
  console.log(`[AURA Frontend] Server running on http://localhost:${PORT}`);
  console.log(`[AURA Frontend] Make sure backend is running on http://localhost:8000`);
});

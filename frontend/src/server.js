/**
 * AURA Frontend Server
 * Express server serving the frontend application with authentication
 */

const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

// Middleware
app.use(express.json());

// Inject API configuration
app.get('/api-config.js', (req, res) => {
    res.setHeader('Content-Type', 'application/javascript');
    res.send(`window.API_CONFIG = { baseUrl: '${API_BASE_URL}' };`);
});

app.use(express.static('public'));

// Serve landing page as default
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/landing.html'));
});

// Serve landing page explicitly
app.get('/landing', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/landing.html'));
});

// Serve landing page explicitly
app.get('/landing.html', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/landing.html'));
});

// Serve main app (protected - client-side auth check)
app.get('/app', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Serve main app index.html
app.get('/index.html', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Logout route - clears tokens and redirects
app.get('/logout', (req, res) => {
  res.redirect('/landing.html');
});

// Start server
app.listen(PORT, () => {
  console.log(`[AURA Frontend] Server running on http://localhost:${PORT}`);
  console.log(`[AURA Frontend] Landing page: http://localhost:${PORT}/`);
  console.log(`[AURA Frontend] App: http://localhost:${PORT}/index.html`);
  console.log(`[AURA Frontend] Make sure backend is running on http://localhost:8000`);
});

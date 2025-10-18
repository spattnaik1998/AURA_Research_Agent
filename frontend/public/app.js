/**
 * AURA Frontend Application
 * Handles UI interactions and API calls
 */

const API_BASE_URL = 'http://localhost:8000';
let currentSessionId = null;
let currentConversationId = null;
let pollingInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkBackendConnection();
    loadAvailableSessions();
});

/**
 * Check if backend is available
 */
async function checkBackendConnection() {
    const statusDiv = document.getElementById('connection-status');
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="w-3 h-3 rounded-full bg-green-500"></div>
                <span class="text-sm text-gray-600">Connected</span>
            `;
        } else {
            throw new Error('Backend not responding');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="w-3 h-3 rounded-full bg-red-500"></div>
            <span class="text-sm text-gray-600">Disconnected</span>
        `;
        console.error('Backend connection error:', error);
    }
}

/**
 * Switch between tabs
 */
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(panel => {
        panel.classList.add('hidden');
    });
    document.getElementById(`panel-${tabName}`).classList.remove('hidden');

    // Load sessions when switching to chatbot tab
    if (tabName === 'chatbot') {
        loadAvailableSessions();
    }
}

/**
 * Start research process
 */
async function startResearch() {
    const query = document.getElementById('research-query').value.trim();

    if (!query) {
        alert('Please enter a research query');
        return;
    }

    // Disable button
    const btn = document.getElementById('start-research-btn');
    btn.disabled = true;
    btn.textContent = 'Starting Research...';

    try {
        // Show status tracker
        document.getElementById('status-tracker').classList.remove('hidden');

        // Generate session ID
        const timestamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0].replace('T', '_');
        currentSessionId = timestamp;
        document.getElementById('session-id').textContent = currentSessionId;

        // Note: In a real implementation, you would call the backend orchestrator here
        // For now, we'll simulate the research process
        alert('Research functionality requires backend orchestrator integration.\n\nTo test with existing data:\n1. Switch to RAG Chatbot tab\n2. Select a research session\n3. Ask questions about the research');

        // Reset UI
        updateProgressStep('step-fetching', 'pending');
        updateProgressStep('step-analyzing', 'pending');
        updateProgressStep('step-synthesizing', 'pending');

    } catch (error) {
        console.error('Research error:', error);
        alert('Failed to start research: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Start Research';
    }
}

/**
 * Update progress step status
 */
function updateProgressStep(stepId, status) {
    const step = document.getElementById(stepId);
    const circle = step.querySelector('.w-8');

    if (status === 'active') {
        circle.classList.remove('bg-gray-200', 'bg-green-500');
        circle.classList.add('bg-primary-600');
        circle.innerHTML = '<div class="w-3 h-3 bg-white rounded-full animate-pulse"></div>';
    } else if (status === 'complete') {
        circle.classList.remove('bg-gray-200', 'bg-primary-600');
        circle.classList.add('bg-green-500');
        circle.innerHTML = '<span class="text-white text-sm">✓</span>';
    } else {
        circle.classList.remove('bg-primary-600', 'bg-green-500');
        circle.classList.add('bg-gray-200');
    }
}

/**
 * Load available research sessions
 */
async function loadAvailableSessions() {
    const selector = document.getElementById('session-selector');

    try {
        const response = await fetch(`${API_BASE_URL}/chat/sessions`);
        const data = await response.json();

        if (data.sessions && data.sessions.length > 0) {
            selector.innerHTML = '<option value="">Select a session...</option>';

            data.sessions.forEach(session => {
                const option = document.createElement('option');
                option.value = session.session_id;
                option.textContent = `Session ${session.session_id}`;
                selector.appendChild(option);
            });
        } else {
            selector.innerHTML = '<option value="">No sessions available</option>';
        }
    } catch (error) {
        console.error('Failed to load sessions:', error);
        selector.innerHTML = '<option value="">Error loading sessions</option>';
    }
}

/**
 * Load selected session
 */
function loadSession() {
    const selector = document.getElementById('session-selector');
    currentSessionId = selector.value;

    if (currentSessionId) {
        // Generate conversation ID
        currentConversationId = 'conv_' + Date.now();

        // Enable chat input
        document.getElementById('chat-input').disabled = false;
        document.getElementById('send-btn').disabled = false;

        // Clear chat
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = `
            <div class="text-center text-gray-500 py-4">
                <p class="font-medium">Session loaded: ${currentSessionId}</p>
                <p class="text-sm">Ask questions about the research findings</p>
            </div>
        `;
    } else {
        document.getElementById('chat-input').disabled = true;
        document.getElementById('send-btn').disabled = true;
    }
}

/**
 * Send chat message
 */
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message || !currentSessionId) {
        return;
    }

    // Clear input
    input.value = '';

    // Add user message to chat
    addMessageToChat('user', message);

    // Disable send button
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;
    sendBtn.textContent = 'Thinking...';

    try {
        const response = await fetch(`${API_BASE_URL}/chat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId,
                conversation_id: currentConversationId
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to send message');
        }

        const data = await response.json();

        // Add assistant response to chat
        addMessageToChat('assistant', data.response);

    } catch (error) {
        console.error('Chat error:', error);
        addMessageToChat('error', 'Failed to get response: ' + error.message);
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Send';
    }
}

/**
 * Add message to chat UI
 */
function addMessageToChat(role, content) {
    const chatMessages = document.getElementById('chat-messages');

    const messageDiv = document.createElement('div');

    if (role === 'user') {
        messageDiv.className = 'chat-message user';
        messageDiv.innerHTML = `
            <p class="text-sm font-medium text-gray-700 mb-1">You</p>
            <p class="text-sm text-gray-900">${escapeHtml(content)}</p>
        `;
    } else if (role === 'assistant') {
        messageDiv.className = 'chat-message assistant';
        messageDiv.innerHTML = `
            <p class="text-sm font-medium text-gray-700 mb-1">AURA Assistant</p>
            <div class="text-sm text-gray-900 whitespace-pre-wrap">${escapeHtml(content)}</div>
        `;
    } else if (role === 'error') {
        messageDiv.className = 'p-3 bg-red-50 border border-red-200 rounded-lg';
        messageDiv.innerHTML = `
            <p class="text-sm text-red-800">${escapeHtml(content)}</p>
        `;
    }

    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Handle Enter key in chat input
 */
function handleChatKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

/**
 * Download essay (placeholder)
 */
function downloadEssay() {
    alert('Essay download functionality requires backend API endpoint.\n\nThe essay file is saved in:\naura_research/storage/essays/');
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Periodic connection check
setInterval(checkBackendConnection, 30000);

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

        // Start research via API
        const response = await fetch(`${API_BASE_URL}/research/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to start research');
        }

        const data = await response.json();
        currentSessionId = data.session_id;
        document.getElementById('session-id').textContent = currentSessionId;

        // Reset progress steps
        updateProgressStep('step-fetching', 'pending');
        updateProgressStep('step-analyzing', 'pending');
        updateProgressStep('step-synthesizing', 'pending');

        // Start polling for status
        startStatusPolling();

    } catch (error) {
        console.error('Research error:', error);
        alert('Failed to start research: ' + error.message);

        // Re-enable button
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
 * Start polling for research status
 */
function startStatusPolling() {
    // Clear any existing polling
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    // Poll every 2 seconds
    pollingInterval = setInterval(async () => {
        try {
            await updateResearchStatus();
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 2000);

    // Initial status check
    updateResearchStatus();
}

/**
 * Update research status from API
 */
async function updateResearchStatus() {
    if (!currentSessionId) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/research/status/${currentSessionId}`);

        if (!response.ok) {
            throw new Error('Failed to get status');
        }

        const status = await response.json();

        // Update progress based on current step
        updateProgressBasedOnStep(status.current_step);

        // Update statistics
        updateResearchStatistics(status.progress);

        // Check if completed
        if (status.status === 'completed') {
            handleResearchComplete(status);
        } else if (status.status === 'failed') {
            handleResearchFailed(status);
        }

    } catch (error) {
        console.error('Status update error:', error);
    }
}

/**
 * Update progress indicators based on current step
 */
function updateProgressBasedOnStep(currentStep) {
    switch (currentStep) {
        case 'initializing':
        case 'fetching_papers':
            updateProgressStep('step-fetching', 'active');
            updateProgressStep('step-analyzing', 'pending');
            updateProgressStep('step-synthesizing', 'pending');
            break;

        case 'analyzing':
            updateProgressStep('step-fetching', 'complete');
            updateProgressStep('step-analyzing', 'active');
            updateProgressStep('step-synthesizing', 'pending');
            break;

        case 'synthesizing':
            updateProgressStep('step-fetching', 'complete');
            updateProgressStep('step-analyzing', 'complete');
            updateProgressStep('step-synthesizing', 'active');
            break;

        case 'completed':
            updateProgressStep('step-fetching', 'complete');
            updateProgressStep('step-analyzing', 'complete');
            updateProgressStep('step-synthesizing', 'complete');
            break;
    }
}

/**
 * Update research statistics display
 */
function updateResearchStatistics(progress) {
    if (progress) {
        document.getElementById('papers-count').textContent = progress.papers_analyzed || 0;
        document.getElementById('agents-count').textContent = `${progress.agents_completed || 0}/3`;
        document.getElementById('word-count').textContent = progress.word_count || 0;
    }
}

/**
 * Handle research completion
 */
function handleResearchComplete(status) {
    // Stop polling
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }

    // Update all steps to complete
    updateProgressStep('step-fetching', 'complete');
    updateProgressStep('step-analyzing', 'complete');
    updateProgressStep('step-synthesizing', 'complete');

    // Show download section
    document.getElementById('download-section').classList.remove('hidden');

    // Re-enable start button
    const btn = document.getElementById('start-research-btn');
    btn.disabled = false;
    btn.textContent = 'Start Research';

    // Show success notification
    showNotification('Research completed successfully!', 'success');

    // Automatically switch to RAG Chatbot tab after 2 seconds
    setTimeout(() => {
        switchTab('chatbot');
        // Reload sessions to show the new one
        loadAvailableSessions();
        // Show notification in chatbot tab
        showNotification('Research complete! Select the session to ask questions.', 'info');
    }, 2000);
}

/**
 * Handle research failure
 */
function handleResearchFailed(status) {
    // Stop polling
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }

    // Re-enable start button
    const btn = document.getElementById('start-research-btn');
    btn.disabled = false;
    btn.textContent = 'Start Research';

    // Show error
    alert(`Research failed: ${status.error || 'Unknown error'}`);
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-green-100 border border-green-400 text-green-800' :
        type === 'error' ? 'bg-red-100 border border-red-400 text-red-800' :
        'bg-blue-100 border border-blue-400 text-blue-800'
    }`;
    notification.innerHTML = `
        <div class="flex items-center space-x-2">
            <span class="text-sm font-medium">${escapeHtml(message)}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="text-gray-500 hover:text-gray-700">
                ✕
            </button>
        </div>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
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

/**
 * AURA Frontend Application
 * Handles UI interactions and API calls
 */

const API_BASE_URL = 'http://localhost:8000';
let currentSessionId = null;
let currentConversationId = null;
let pollingInterval = null;
let currentInputMode = 'text'; // 'text' or 'image'
let uploadedImageData = null;
let extractedQuery = null;
let currentUser = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication first
    const isAuthenticated = await checkAuthentication();
    if (!isAuthenticated) {
        // Redirect to landing page
        window.location.href = '/landing.html';
        return;
    }

    // Display user info
    displayUserInfo();

    // Initialize app
    initializeTheme();
    checkBackendConnection();
    loadAvailableSessions();
});

/**
 * Check if user is authenticated
 */
async function checkAuthentication() {
    const token = localStorage.getItem('aura_access_token');

    if (!token) {
        return false;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/auth/verify`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (data.valid && data.user) {
            currentUser = data.user;
            localStorage.setItem('aura_user', JSON.stringify(data.user));
            return true;
        } else {
            // Try to refresh the token
            const refreshed = await refreshAccessToken();
            return refreshed;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        return false;
    }
}

/**
 * Refresh access token using refresh token
 */
async function refreshAccessToken() {
    const refreshToken = localStorage.getItem('aura_refresh_token');

    if (!refreshToken) {
        return false;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('aura_access_token', data.access_token);
            localStorage.setItem('aura_refresh_token', data.refresh_token);
            return true;
        } else {
            // Refresh failed, clear tokens
            clearAuthTokens();
            return false;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    }
}

/**
 * Get authorization headers for API requests
 */
function getAuthHeaders() {
    const token = localStorage.getItem('aura_access_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

/**
 * Display user info in the header
 */
function displayUserInfo() {
    const user = currentUser || JSON.parse(localStorage.getItem('aura_user') || 'null');

    if (user) {
        // Create user info element if it doesn't exist
        let userInfoDiv = document.getElementById('user-info');

        if (!userInfoDiv) {
            // Find the header controls and add user info before it
            const headerControls = document.getElementById('header-controls');
            if (headerControls) {
                userInfoDiv = document.createElement('div');
                userInfoDiv.id = 'user-info';
                userInfoDiv.className = 'flex items-center gap-4';
                userInfoDiv.innerHTML = `
                    <div class="flex items-center gap-2 px-3 py-2 rounded-lg" style="background-color: var(--bg-elevated);">
                        <div class="w-7 h-7 rounded-full flex items-center justify-center text-white text-sm font-semibold" style="background-color: var(--accent-primary);">
                            ${(user.username || 'U').charAt(0).toUpperCase()}
                        </div>
                        <span class="text-sm font-medium" style="color: var(--text-secondary);">
                            ${user.full_name || user.username}
                        </span>
                    </div>
                    <button onclick="logout()" class="p-2 rounded-lg transition" style="color: var(--text-secondary); background: transparent;" onmouseover="this.style.backgroundColor='var(--bg-elevated)'" onmouseout="this.style.backgroundColor='transparent'" title="Logout">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                    </button>
                `;
                headerControls.parentElement.insertBefore(userInfoDiv, headerControls);
            }
        }
    }
}

/**
 * Logout user
 */
async function logout() {
    const token = localStorage.getItem('aura_access_token');

    if (token) {
        try {
            await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
        } catch (error) {
            console.error('Logout API call failed:', error);
        }
    }

    clearAuthTokens();
    window.location.href = '/landing.html';
}

/**
 * Clear authentication tokens
 */
function clearAuthTokens() {
    localStorage.removeItem('aura_access_token');
    localStorage.removeItem('aura_refresh_token');
    localStorage.removeItem('aura_user');
    currentUser = null;
}

/**
 * Get current user ID for API requests
 */
function getCurrentUserId() {
    const user = currentUser || JSON.parse(localStorage.getItem('aura_user') || 'null');
    return user ? user.user_id : null;
}

/**
 * Initialize theme from localStorage or system preference
 */
function initializeTheme() {
    // Check localStorage first
    const savedTheme = localStorage.getItem('aura-theme');

    if (savedTheme) {
        applyTheme(savedTheme);
    } else {
        // Check system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        applyTheme(prefersDark ? 'dark' : 'light');
    }
}

/**
 * Apply theme to document
 */
function applyTheme(theme) {
    const html = document.documentElement;
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');

    if (theme === 'dark') {
        html.setAttribute('data-theme', 'dark');
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
    } else {
        html.removeAttribute('data-theme');
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    }

    // Save to localStorage
    localStorage.setItem('aura-theme', theme);
}

/**
 * Toggle between light and dark theme
 */
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    applyTheme(newTheme);

    // Add animation feedback
    const toggleButton = document.getElementById('theme-toggle');
    toggleButton.style.transform = 'scale(0.9) rotate(180deg)';
    setTimeout(() => {
        toggleButton.style.transform = '';
    }, 300);
}

/**
 * Check if backend is available
 */
async function checkBackendConnection() {
    const statusDiv = document.getElementById('connection-status');
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="w-2 h-2 rounded-full" style="background-color: #22C55E;"></div>
                <span class="text-xs font-medium" style="color: #166534;">Connected</span>
            `;
            statusDiv.style.cssText = 'display: flex; align-items: center; gap: 0.5rem; padding: 0.375rem 0.75rem; border-radius: 9999px; background-color: #F0FDF4; border: 1px solid #BBF7D0;';
        } else {
            throw new Error('Backend not responding');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="w-2 h-2 rounded-full" style="background-color: #EF4444;"></div>
            <span class="text-xs font-medium" style="color: #991B1B;">Disconnected</span>
        `;
        statusDiv.style.cssText = 'display: flex; align-items: center; gap: 0.5rem; padding: 0.375rem 0.75rem; border-radius: 9999px; background-color: #FEF2F2; border: 1px solid #FECACA;';
        console.error('Backend connection error:', error);
    }
}

/**
 * Switch between tabs
 */
function switchTab(tabName) {
    // Update tab buttons - use correct selector
    document.querySelectorAll('.nav-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');

    // Update tab content - use correct class
    document.querySelectorAll('.tab-content').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(`panel-${tabName}`).classList.add('active');

    // Scroll to the active panel
    const activePanel = document.getElementById(`panel-${tabName}`);
    if (activePanel) {
        activePanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Load sessions when switching to chatbot tab
    if (tabName === 'chatbot') {
        loadAvailableSessions();
    }
}

/**
 * Switch between text and image input modes
 */
function switchInputMode(mode) {
    currentInputMode = mode;

    // Update button states
    const textBtn = document.getElementById('text-mode-btn');
    const imageBtn = document.getElementById('image-mode-btn');

    if (mode === 'text') {
        textBtn.classList.add('active');
        imageBtn.classList.remove('active');
        document.getElementById('text-input-section').classList.remove('hidden');
        document.getElementById('image-input-section').classList.add('hidden');
    } else {
        imageBtn.classList.add('active');
        textBtn.classList.remove('active');
        document.getElementById('text-input-section').classList.add('hidden');
        document.getElementById('image-input-section').classList.remove('hidden');
    }
}

/**
 * Handle image upload
 */
async function handleImageUpload(event) {
    const file = event.target.files[0];

    if (!file) {
        return;
    }

    // Validate file type
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
        alert('Please upload a PNG or JPEG image');
        return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert('Image size must be less than 10MB');
        return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = async function(e) {
        uploadedImageData = e.target.result;

        // Update preview UI
        document.getElementById('image-preview').src = uploadedImageData;
        document.getElementById('image-filename').textContent = file.name;
        document.getElementById('image-preview-section').classList.remove('hidden');
        document.getElementById('image-upload-area').classList.add('hidden');

        // Extract query from image
        await extractQueryFromImage(uploadedImageData);
    };

    reader.readAsDataURL(file);
}

/**
 * Extract research query from uploaded image using GPT-4 Vision
 */
async function extractQueryFromImage(imageData) {
    const extractedSection = document.getElementById('extracted-query-section');
    const extractedText = document.getElementById('extracted-query-text');

    // Show loading state
    extractedSection.classList.remove('hidden');
    extractedText.innerHTML = '<span class="text-gray-500 italic">Analyzing image...</span>';

    try {
        const response = await fetch(`${API_BASE_URL}/research/analyze-image`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image_data: imageData
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to analyze image');
        }

        const data = await response.json();
        extractedQuery = data.query;

        // Display extracted query
        extractedText.textContent = extractedQuery;

    } catch (error) {
        console.error('Image analysis error:', error);
        extractedText.innerHTML = '<span class="text-red-600">Failed to analyze image. Please try again or enter a text query instead.</span>';
        extractedQuery = null;
    }
}

/**
 * Clear image upload
 */
function clearImageUpload() {
    // Reset upload
    document.getElementById('research-image').value = '';
    uploadedImageData = null;
    extractedQuery = null;

    // Reset UI
    document.getElementById('image-preview-section').classList.add('hidden');
    document.getElementById('image-upload-area').classList.remove('hidden');
    document.getElementById('extracted-query-section').classList.add('hidden');
}

/**
 * Start research process
 */
async function startResearch() {
    let query = '';

    // Get query based on input mode
    if (currentInputMode === 'text') {
        query = document.getElementById('research-query').value.trim();

        if (!query) {
            alert('Please enter a research query');
            return;
        }
    } else {
        // Image mode
        if (!uploadedImageData) {
            alert('Please upload an image');
            return;
        }

        if (!extractedQuery) {
            alert('Waiting for image analysis to complete. Please try again in a moment.');
            return;
        }

        query = extractedQuery;
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
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                query: query,
                user_id: getCurrentUserId()
            })
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
    const circle = step.querySelector('.w-12');

    // Reset all classes first
    step.className = 'progress-step p-4 rounded-xl transition-all';
    circle.className = 'relative w-12 h-12 rounded-full flex items-center justify-center';

    if (status === 'active') {
        step.style.cssText = 'background-color: #DBEAFE; border: 1px solid #93C5FD;';
        circle.style.cssText = 'background-color: #1E40AF;';
        circle.innerHTML = '<div class="w-4 h-4 bg-white rounded-full animate-pulse"></div>';
    } else if (status === 'complete') {
        step.style.cssText = 'background-color: #F0FDF4; border: 1px solid #BBF7D0;';
        circle.style.cssText = 'background-color: #22C55E;';
        circle.innerHTML = '<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>';
    } else {
        step.style.cssText = 'background-color: #F5F5F5; border: 1px solid #E5E7EB;';
        circle.style.cssText = 'background-color: #E5E7EB;';
        // Keep original number content
    }
}

/**
 * Load available research sessions
 */
async function loadAvailableSessions() {
    const selector = document.getElementById('session-selector');

    try {
        // Get sessions filtered by current user
        const userId = getCurrentUserId();
        console.log('[Sessions] Loading sessions for user_id:', userId);

        const url = userId
            ? `${API_BASE_URL}/chat/sessions?user_id=${userId}`
            : `${API_BASE_URL}/chat/sessions`;

        console.log('[Sessions] Fetching from:', url);
        const response = await fetch(url, {
            headers: {
                ...getAuthHeaders()
            }
        });
        const data = await response.json();
        console.log('[Sessions] Received:', data.count, 'sessions');

        if (data.sessions && data.sessions.length > 0) {
            selector.innerHTML = '<option value="">Select a research session...</option>';

            data.sessions.forEach(session => {
                const option = document.createElement('option');
                option.value = session.session_id;

                // Display query name with date
                const queryText = session.query.length > 60
                    ? session.query.substring(0, 60) + '...'
                    : session.query;

                option.textContent = `${queryText} (${session.date})`;
                option.title = `${session.query} - ${session.date}`;  // Full text on hover
                selector.appendChild(option);
            });
        } else {
            selector.innerHTML = '<option value="">No research sessions available yet</option>';
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

    // Get selected language
    const languageSelector = document.getElementById('language-selector');
    const selectedLanguage = languageSelector.value || 'English';

    // Clear input
    input.value = '';

    // Add user message to chat
    addMessageToChat('user', message);

    // Show thinking indicator
    addThinkingIndicator();

    // Disable send button
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;
    sendBtn.textContent = 'Thinking...';

    try {
        const response = await fetch(`${API_BASE_URL}/chat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId,
                conversation_id: currentConversationId,
                language: selectedLanguage,
                user_id: getCurrentUserId()
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to send message');
        }

        const data = await response.json();

        // Remove thinking indicator
        removeThinkingIndicator();

        // Add assistant response to chat
        addMessageToChat('assistant', data.response);

    } catch (error) {
        console.error('Chat error:', error);

        // Remove thinking indicator on error
        removeThinkingIndicator();

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
            <p class="text-xs font-semibold text-blue-800 mb-1">You</p>
            <p class="text-sm text-gray-800">${escapeHtml(content)}</p>
        `;
    } else if (role === 'assistant') {
        messageDiv.className = 'chat-message assistant';
        messageDiv.innerHTML = `
            <div class="flex items-center gap-2 mb-2">
                <div class="w-7 h-7 rounded-lg flex items-center justify-center" style="background-color: #1E40AF;">
                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                    </svg>
                </div>
                <p class="text-xs font-semibold text-gray-700">AURA Assistant</p>
            </div>
            <div class="assistant-response text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">${formatMarkdown(content)}</div>
        `;
    } else if (role === 'error') {
        messageDiv.className = 'p-3 rounded-lg';
        messageDiv.style.cssText = 'background-color: #FEF2F2; border: 1px solid #FECACA;';
        messageDiv.innerHTML = `
            <p class="text-sm text-red-800">${escapeHtml(content)}</p>
        `;
    }

    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Format markdown-like content for display
 */
function formatMarkdown(text) {
    let formatted = escapeHtml(text);

    // Format headers (##)
    formatted = formatted.replace(/^## (.+)$/gm, '<h3 class="text-base font-semibold text-gray-900 mt-3 mb-2 first:mt-0">$1</h3>');

    // Format bold (**text**)
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-gray-900">$1</strong>');

    // Format bullet points (• or -)
    formatted = formatted.replace(/^[•\-] (.+)$/gm, '<div class="flex gap-2 ml-4 my-1"><span style="color: #1E40AF;">•</span><span>$1</span></div>');

    // Format checkmarks and X marks
    formatted = formatted.replace(/✓/g, '<span style="color: #16A34A; font-weight: 600;">✓</span>');
    formatted = formatted.replace(/✗/g, '<span style="color: #DC2626; font-weight: 600;">✗</span>');

    return formatted;
}

/**
 * Add thinking indicator to chat
 */
function addThinkingIndicator() {
    const chatMessages = document.getElementById('chat-messages');

    const thinkingDiv = document.createElement('div');
    thinkingDiv.id = 'thinking-indicator';
    thinkingDiv.className = 'chat-message assistant';
    thinkingDiv.innerHTML = `
        <div class="flex items-center gap-2 mb-2">
            <div class="w-7 h-7 rounded-lg flex items-center justify-center" style="background-color: #1E40AF;">
                <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                </svg>
            </div>
            <p class="text-xs font-semibold text-gray-700">AURA Assistant</p>
        </div>
        <div class="thinking-indicator">
            <div class="orbital-system">
                <div class="orbit orbit-1"></div>
                <div class="orbit orbit-2"></div>
                <div class="orbit orbit-3"></div>
            </div>
            <div class="thinking-dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <p class="thinking-text">Analyzing research and formulating response...</p>
        </div>
    `;

    chatMessages.appendChild(thinkingDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Remove thinking indicator from chat
 */
function removeThinkingIndicator() {
    const thinkingIndicator = document.getElementById('thinking-indicator');
    if (thinkingIndicator) {
        thinkingIndicator.remove();
    }
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
        const response = await fetch(`${API_BASE_URL}/research/status/${currentSessionId}`, {
            headers: {
                ...getAuthHeaders()
            }
        });

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

    // Initialize audio UI
    initializeAudioUI();

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

    // Use clean, single-color design
    let bgColor, borderColor, textColor;
    if (type === 'success') {
        bgColor = '#F0FDF4';
        borderColor = '#22C55E';
        textColor = '#166534';
    } else if (type === 'error') {
        bgColor = '#FEF2F2';
        borderColor = '#EF4444';
        textColor = '#991B1B';
    } else {
        bgColor = '#DBEAFE';
        borderColor = '#1E40AF';
        textColor = '#1E40AF';
    }

    notification.className = 'fixed top-20 right-4 p-4 rounded-lg z-50';
    notification.style.cssText = `
        background-color: ${bgColor};
        border: 1px solid ${borderColor};
        color: ${textColor};
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        animation: slideUp 0.3s ease-out;
    `;

    const icon = type === 'success' ?
        '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>' :
        type === 'error' ?
        '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>' :
        '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>';

    notification.innerHTML = `
        <div class="flex items-center space-x-3">
            ${icon}
            <span class="text-sm font-medium flex-1">${escapeHtml(message)}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-3 opacity-60 hover:opacity-100 transition-opacity">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                </svg>
            </button>
        </div>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds with fade-out animation
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-10px)';
        notification.style.transition = 'all 0.2s ease-out';
        setTimeout(() => notification.remove(), 200);
    }, 5000);
}

/**
 * Audio playback state
 */
let audioState = { exists: false, generating: false, currentSessionId: null };

/**
 * Check if audio exists for current session
 */
async function checkAudioStatus() {
    if (!currentSessionId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/research/session/${currentSessionId}/audio/status`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) return;

        const data = await response.json();
        audioState.exists = data.exists;
        updateAudioUI();
    } catch (error) {
        console.error('Error checking audio status:', error);
    }
}

/**
 * Update audio UI based on state
 */
function updateAudioUI() {
    const btnText = document.getElementById('audio-btn-text');
    const statusMsg = document.getElementById('audio-status-msg');

    if (!btnText || !statusMsg) return;

    if (audioState.exists) {
        btnText.textContent = 'Play Audio';
        statusMsg.textContent = 'Audio is ready to play. Click the button to listen.';
    } else {
        btnText.textContent = 'Generate Audio';
        statusMsg.textContent = 'Convert your essay to speech';
    }
}

/**
 * Handle audio button click (generate or play)
 */
async function handleAudioAction() {
    if (audioState.generating) return;

    if (audioState.exists) {
        await playAudio();
    } else {
        await generateAudio();
    }
}

/**
 * Generate audio from essay
 */
async function generateAudio() {
    if (!currentSessionId) {
        showNotification('No active session', 'error');
        return;
    }

    audioState.generating = true;

    // Show loading state
    const btnText = document.getElementById('audio-btn-text');
    const spinner = document.getElementById('audio-spinner');

    if (btnText) btnText.textContent = 'Generating...';
    if (spinner) spinner.classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE_URL}/research/session/${currentSessionId}/generate-audio`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate audio');
        }

        audioState.exists = true;
        showNotification('Audio generated successfully!', 'success');
        updateAudioUI();

        // Auto-play
        await playAudio();

    } catch (error) {
        showNotification('Failed to generate audio: ' + error.message, 'error');
    } finally {
        audioState.generating = false;
        if (spinner) spinner.classList.add('hidden');
        updateAudioUI();
    }
}

/**
 * Play audio
 */
async function playAudio() {
    if (!currentSessionId) return;

    try {
        const token = localStorage.getItem('aura_access_token');
        const response = await fetch(`${API_BASE_URL}/research/session/${currentSessionId}/audio`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch audio');
        }

        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        const audioPlayer = document.getElementById('essay-audio-player');
        const audioSource = document.getElementById('essay-audio-source');

        if (audioPlayer && audioSource) {
            audioSource.src = audioUrl;
            audioPlayer.load();
            audioPlayer.classList.remove('hidden');
            audioPlayer.play();
        }

        const btnText = document.getElementById('audio-btn-text');
        if (btnText) btnText.textContent = 'Play Audio';

    } catch (error) {
        showNotification('Failed to play audio: ' + error.message, 'error');
    }
}

/**
 * Initialize audio UI when research completes
 */
function initializeAudioUI() {
    audioState.currentSessionId = currentSessionId;
    checkAudioStatus();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * ============================================
 * KNOWLEDGE GRAPH FUNCTIONS
 * ============================================
 */

/**
 * Load available sessions for graph selector
 */
async function loadGraphSessions() {
    try {
        // Get sessions filtered by current user
        const userId = getCurrentUserId();
        const url = userId
            ? `${API_BASE_URL}/chat/sessions?user_id=${userId}`
            : `${API_BASE_URL}/chat/sessions`;

        const response = await fetch(url, {
            headers: {
                ...getAuthHeaders()
            }
        });
        const data = await response.json();

        const selector = document.getElementById('graph-session-selector');
        if (!selector) return;

        if (data.sessions && data.sessions.length > 0) {
            selector.innerHTML = '<option value="">Select a session...</option>';
            data.sessions.forEach(session => {
                const option = document.createElement('option');
                option.value = session.session_id;
                option.textContent = `${session.query} (${session.date})`;
                selector.appendChild(option);
            });
        } else {
            selector.innerHTML = '<option value="">No research sessions available</option>';
        }
    } catch (error) {
        console.error('Error loading graph sessions:', error);
        const selector = document.getElementById('graph-session-selector');
        if (selector) {
            selector.innerHTML = '<option value="">Error loading sessions</option>';
        }
    }
}

/**
 * Load graph for selected session
 */
async function loadGraphSession() {
    const selector = document.getElementById('graph-session-selector');
    const sessionId = selector.value;

    if (!sessionId) {
        return;
    }

    try {
        // Enable refresh button
        const refreshBtn = document.getElementById('refresh-graph-btn');
        if (refreshBtn) {
            refreshBtn.disabled = false;
        }

        // Initialize graph visualizer if not already initialized
        const viz = initGraphVisualizer();

        // Load the graph
        await viz.loadGraph(sessionId);

        showNotification('Knowledge graph loaded successfully!', 'success');
    } catch (error) {
        console.error('Error loading graph:', error);
        showNotification('Failed to load knowledge graph: ' + error.message, 'error');
    }
}

/**
 * Refresh/rebuild the current graph
 */
async function refreshGraph() {
    const selector = document.getElementById('graph-session-selector');
    const sessionId = selector.value;

    if (!sessionId) {
        showNotification('Please select a research session first', 'info');
        return;
    }

    try {
        showNotification('Rebuilding knowledge graph...', 'info');

        // Clear cache and rebuild
        await fetch(`${API_BASE_URL}/graph/cache/${sessionId}`, {
            method: 'DELETE',
            headers: {
                ...getAuthHeaders()
            }
        });

        // Rebuild graph
        const response = await fetch(`${API_BASE_URL}/graph/build/${sessionId}`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders()
            }
        });

        if (!response.ok) {
            throw new Error('Failed to rebuild graph');
        }

        const buildData = await response.json();

        // Use graph data directly from build response
        const viz = initGraphVisualizer();
        if (buildData.success && buildData.graph) {
            viz.graphData = buildData.graph;
            viz.currentSessionId = sessionId;
            viz.render();
            await viz.loadAnalysis(sessionId);
        } else {
            throw new Error('Build returned no graph data');
        }

        showNotification('Knowledge graph rebuilt successfully!', 'success');
    } catch (error) {
        console.error('Error rebuilding graph:', error);
        showNotification('Failed to rebuild graph: ' + error.message, 'error');
    }
}

// Update switchTab to load graph sessions when switching to graph tab
const originalSwitchTab = switchTab;
switchTab = function(tabName) {
    originalSwitchTab(tabName);

    // Load graph sessions when switching to graph tab
    if (tabName === 'graph') {
        loadGraphSessions();
    }

    // Load sessions when switching to questions tab
    if (tabName === 'questions') {
        loadQuestionSessions();
    }
};

/**
 * ============================================
 * QUESTION GENERATOR FUNCTIONS
 * ============================================
 */

let currentQuestionsData = null;
let allQuestions = [];

/**
 * Load available sessions for question generator
 */
async function loadQuestionSessions() {
    try {
        // Get sessions filtered by current user
        const userId = getCurrentUserId();
        const url = userId
            ? `${API_BASE_URL}/chat/sessions?user_id=${userId}`
            : `${API_BASE_URL}/chat/sessions`;

        const response = await fetch(url, {
            headers: {
                ...getAuthHeaders()
            }
        });
        const data = await response.json();

        const selector = document.getElementById('questions-session-selector');
        if (!selector) return;

        if (data.sessions && data.sessions.length > 0) {
            selector.innerHTML = '<option value="">Select a session...</option>';
            data.sessions.forEach(session => {
                const option = document.createElement('option');
                option.value = session.session_id;
                option.textContent = `${session.query} (${session.date})`;
                selector.appendChild(option);
            });

            // Enable generate button when session selected
            selector.addEventListener('change', () => {
                const btn = document.getElementById('generate-questions-btn');
                btn.disabled = !selector.value;
            });
        } else {
            selector.innerHTML = '<option value="">No research sessions available</option>';
        }
    } catch (error) {
        console.error('Error loading question sessions:', error);
    }
}

/**
 * Generate research questions
 */
async function generateQuestions() {
    const selector = document.getElementById('questions-session-selector');
    const sessionId = selector.value;

    if (!sessionId) {
        showNotification('Please select a research session', 'info');
        return;
    }

    try {
        // Get options
        const includeGaps = document.getElementById('include-gaps-checkbox').checked;
        const numQuestions = parseInt(document.getElementById('num-questions-input').value) || 15;

        // Show loading
        document.getElementById('questions-loading').classList.remove('hidden');
        document.getElementById('gaps-section').classList.add('hidden');
        document.getElementById('questions-section').classList.add('hidden');
        document.getElementById('questions-stats').classList.add('hidden');

        // Disable button
        const btn = document.getElementById('generate-questions-btn');
        btn.disabled = true;
        btn.textContent = 'Generating...';

        // Call API
        const response = await fetch(
            `${API_BASE_URL}/ideation/generate-questions/${sessionId}?num_questions=${numQuestions}&include_gaps=${includeGaps}`,
            {
                method: 'POST',
                headers: {
                    ...getAuthHeaders()
                }
            }
        );

        if (!response.ok) {
            throw new Error('Failed to generate questions');
        }

        const result = await response.json();
        currentQuestionsData = result.data;
        allQuestions = result.data.questions || [];

        // Display results
        displayGaps(result.data.gaps_identified || []);
        displayQuestions(allQuestions);
        displayQuestionStats(sessionId);

        // Hide loading
        document.getElementById('questions-loading').classList.add('hidden');

        // Re-enable button
        btn.disabled = false;
        btn.textContent = 'Generate Questions';

        showNotification(`Generated ${allQuestions.length} research questions!`, 'success');

    } catch (error) {
        console.error('Error generating questions:', error);
        document.getElementById('questions-loading').classList.add('hidden');

        const btn = document.getElementById('generate-questions-btn');
        btn.disabled = false;
        btn.textContent = 'Generate Questions';

        showNotification('Failed to generate questions: ' + error.message, 'error');
    }
}

/**
 * Display research gaps
 */
function displayGaps(gaps) {
    const container = document.getElementById('gaps-container');
    const section = document.getElementById('gaps-section');

    if (!gaps || gaps.length === 0) {
        section.classList.add('hidden');
        return;
    }

    const gapColors = {
        'methodological': 'blue',
        'theoretical': 'purple',
        'empirical': 'green',
        'practical': 'orange',
        'integration': 'pink'
    };

    container.innerHTML = gaps.map(gap => {
        const color = gapColors[gap.type] || 'gray';
        return `
            <div class="p-4 border border-${color}-200 bg-${color}-50 rounded-lg">
                <div class="flex items-start justify-between mb-2">
                    <h4 class="font-semibold text-gray-900">${escapeHtml(gap.title)}</h4>
                    <div class="flex items-center space-x-2">
                        <span class="px-2 py-1 bg-${color}-100 text-${color}-700 rounded text-xs font-medium">${gap.type}</span>
                        <span class="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">${gap.feasibility}</span>
                    </div>
                </div>
                <p class="text-sm text-gray-700 mb-2">${escapeHtml(gap.description)}</p>
                <p class="text-sm text-gray-600 italic">${escapeHtml(gap.significance)}</p>
            </div>
        `;
    }).join('');

    section.classList.remove('hidden');
}

/**
 * Display questions
 */
function displayQuestions(questions) {
    const container = document.getElementById('questions-container');
    const section = document.getElementById('questions-section');

    if (!questions || questions.length === 0) {
        section.classList.add('hidden');
        return;
    }

    container.innerHTML = questions.map((q, idx) => {
        const scores = q.scores || {};
        const overallScore = q.overall_score || 0;

        return `
            <div class="status-card hover:shadow-lg transition-shadow">
                <div class="flex items-start justify-between mb-3">
                    <div class="flex-1">
                        <div class="flex items-center space-x-2 mb-2">
                            <span class="text-sm font-bold text-purple-600">#${idx + 1}</span>
                            <span class="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium">${q.type}</span>
                            <span class="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-medium">Score: ${overallScore.toFixed(1)}/10</span>
                        </div>
                        <h4 class="text-lg font-semibold text-gray-900 mb-2">${escapeHtml(q.question)}</h4>
                    </div>
                </div>

                <div class="space-y-2 mb-3">
                    <p class="text-sm text-gray-700"><strong>Rationale:</strong> ${escapeHtml(q.rationale)}</p>
                    <p class="text-sm text-gray-700"><strong>Novelty:</strong> ${escapeHtml(q.novelty)}</p>
                    <p class="text-sm text-gray-700"><strong>Scope:</strong> ${escapeHtml(q.scope)}</p>
                    <p class="text-sm text-gray-700"><strong>Methodology:</strong> ${escapeHtml(q.methodology_suggestion)}</p>
                </div>

                <div class="grid grid-cols-5 gap-2 mb-3">
                    ${Object.entries(scores).map(([key, value]) => `
                        <div class="text-center">
                            <div class="text-xs text-gray-600 mb-1 capitalize">${key}</div>
                            <div class="w-full bg-gray-200 rounded-full h-2">
                                <div class="bg-purple-500 h-2 rounded-full" style="width: ${value * 10}%"></div>
                            </div>
                            <div class="text-xs text-gray-700 mt-1">${value}/10</div>
                        </div>
                    `).join('')}
                </div>

                ${q.strengths && q.strengths.length > 0 ? `
                    <div class="mb-2">
                        <p class="text-xs font-semibold text-green-700 mb-1">Strengths:</p>
                        <ul class="list-disc list-inside text-xs text-gray-600 space-y-1">
                            ${q.strengths.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${q.potential_challenges && q.potential_challenges.length > 0 ? `
                    <div>
                        <p class="text-xs font-semibold text-orange-700 mb-1">Challenges:</p>
                        <ul class="list-disc list-inside text-xs text-gray-600 space-y-1">
                            ${q.potential_challenges.map(c => `<li>${escapeHtml(c)}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');

    section.classList.remove('hidden');
}

/**
 * Filter questions by type
 */
function filterQuestions() {
    const filterValue = document.getElementById('question-type-filter').value;

    if (filterValue === 'all') {
        displayQuestions(allQuestions);
    } else {
        const filtered = allQuestions.filter(q => q.type === filterValue);
        displayQuestions(filtered);
    }
}

/**
 * Sort questions
 */
function sortQuestions() {
    const sortValue = document.getElementById('question-sort').value;
    let sorted = [...allQuestions];

    switch(sortValue) {
        case 'score':
            sorted.sort((a, b) => (b.overall_score || 0) - (a.overall_score || 0));
            break;
        case 'novelty':
            sorted.sort((a, b) => (b.scores?.novelty || 0) - (a.scores?.novelty || 0));
            break;
        case 'feasibility':
            sorted.sort((a, b) => (b.scores?.feasibility || 0) - (a.scores?.feasibility || 0));
            break;
        case 'impact':
            sorted.sort((a, b) => (b.scores?.impact || 0) - (a.scores?.impact || 0));
            break;
    }

    allQuestions = sorted;
    const filterValue = document.getElementById('question-type-filter').value;

    if (filterValue === 'all') {
        displayQuestions(sorted);
    } else {
        const filtered = sorted.filter(q => q.type === filterValue);
        displayQuestions(filtered);
    }
}

/**
 * Display question statistics
 */
async function displayQuestionStats(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/ideation/stats/${sessionId}`, {
            headers: {
                ...getAuthHeaders()
            }
        });
        const data = await response.json();

        const stats = data.statistics;
        const container = document.getElementById('stats-content');
        const section = document.getElementById('questions-stats');

        container.innerHTML = `
            <div class="text-center p-4 bg-purple-50 rounded-lg">
                <div class="text-3xl font-bold text-purple-600">${stats.total_questions}</div>
                <div class="text-sm text-gray-600 mt-1">Questions</div>
            </div>
            <div class="text-center p-4 bg-blue-50 rounded-lg">
                <div class="text-3xl font-bold text-blue-600">${stats.total_gaps}</div>
                <div class="text-sm text-gray-600 mt-1">Gaps</div>
            </div>
            <div class="text-center p-4 bg-green-50 rounded-lg">
                <div class="text-3xl font-bold text-green-600">${stats.average_overall_score.toFixed(1)}</div>
                <div class="text-sm text-gray-600 mt-1">Avg Score</div>
            </div>
        `;

        section.classList.remove('hidden');

    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Periodic connection check
setInterval(checkBackendConnection, 30000);

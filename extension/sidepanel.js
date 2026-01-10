/**
 * RAGex Companion - Side Panel Controller (Multi-Session Edition)
 * ==============================================================
 */

const CONFIG = {
    API_BASE: 'http://127.0.0.1:8000/api/v1',
    MAX_PAGES: 3,
    REQUEST_TIMEOUT: 30000
};

// ==================== Session Management ====================
class Session {
    constructor(id) {
        this.id = id;
        this.title = "New Session";
        this.url = null;
        this.isConnected = false;
        this.history = []; // Chat history
        this.analysis = null; // {type, summary, topics}
        this.timestamp = Date.now();
    }
}

const STATE = {
    sessions: [],
    activeSessionId: null,
    isProcessing: false,
    currentChromeTab: null
};

// DOM Cache
const DOM = {};
['overlay', 'overlayText', 'statusBadge', 'tabsContainer', 'urlDisplay', 
 'scanBtn', 'analysisCard', 'acType', 'acSummary', 'acTags', 
 'chatArea', 'userInput', 'sendBtn'].forEach(id => DOM[id] = document.getElementById(id));


// ==================== Initialization ====================
async function initialize() {
    console.log('[RAGex] Initializing...');
    
    setupEventListeners();
    await loadSessions();
    
    // Create default session if none exist
    if (STATE.sessions.length === 0) {
        createNewSession();
    }
    
    // Ensure we have an active session
    if (!STATE.activeSessionId && STATE.sessions.length > 0) {
        switchSession(STATE.sessions[0].id);
    } else {
        renderUI(); // Render existing state
    }

    // Check Chrome tab URL to see if it matches current session
    await checkCurrentTab();
}

function setupEventListeners() {
    DOM.scanBtn.addEventListener('click', handleScanClick);
    DOM.sendBtn.addEventListener('click', handleSendClick);
    DOM.userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) handleSendClick();
    });
}

// ==================== Tab/Session Logic ====================

function createNewSession() {
    const id = Date.now().toString();
    const newSession = new Session(id);
    STATE.sessions.push(newSession);
    switchSession(id);
    saveSessions();
}

function closeSession(id, e) {
    if (e) e.stopPropagation(); // Prevent click from triggering switch
    
    // Don't close the last session, just reset it
    if (STATE.sessions.length === 1) {
        const s = STATE.sessions[0];
        s.title = "New Session";
        s.url = null;
        s.isConnected = false;
        s.history = [];
        s.analysis = null;
        renderUI();
        saveSessions();
        return;
    }

    const index = STATE.sessions.findIndex(s => s.id === id);
    STATE.sessions.splice(index, 1);
    
    // If we closed the active session, switch to the one before it (or first)
    if (id === STATE.activeSessionId) {
        const newActive = STATE.sessions[Math.max(0, index - 1)];
        switchSession(newActive.id);
    } else {
        renderTabs(); // Just re-render tabs
    }
    saveSessions();
}

function switchSession(id) {
    console.log(`[RAGex] Switching to session ${id}`);
    STATE.activeSessionId = id;
    renderUI();
}

function getActiveSession() {
    return STATE.sessions.find(s => s.id === STATE.activeSessionId);
}

// ==================== UI Rendering ====================

function renderUI() {
    const session = getActiveSession();
    if (!session) return;

    renderTabs();
    
    // 1. Update Connection UI
    DOM.urlDisplay.textContent = session.url ? new URL(session.url).hostname : "No Page Connected";
    DOM.statusBadge.textContent = session.isConnected ? "Connected" : "Disconnected";
    DOM.statusBadge.className = `status-badge ${session.isConnected ? 'active' : ''}`;
    
    DOM.scanBtn.textContent = session.isConnected ? "Re-Scan" : "Connect";
    DOM.userInput.disabled = !session.isConnected;
    DOM.sendBtn.disabled = !session.isConnected;

    // 2. Update Analysis Card
    if (session.analysis) {
        DOM.analysisCard.classList.add('visible');
        DOM.acType.textContent = session.analysis.type;
        DOM.acSummary.innerHTML = formatSummaryAsBullets(session.analysis.summary);
        DOM.acTags.innerHTML = session.analysis.topics.map(t => `<span class="ac-tag">#${t}</span>`).join('');
    } else {
        DOM.analysisCard.classList.remove('visible');
    }

    // 3. Rebuild Chat History
    DOM.chatArea.innerHTML = ''; 
    // Re-append analysis card to top of chat area
    DOM.chatArea.appendChild(DOM.analysisCard); 

    // Add welcome msg if empty
    if (session.history.length === 0) {
        const welcome = document.createElement('div');
        welcome.className = 'msg-row bot';
        welcome.innerHTML = `<div class="msg bot"><strong>Welcome!</strong><br>Click Connect to analyze the current page in this tab.</div>`;
        DOM.chatArea.appendChild(welcome);
    } else {
        session.history.forEach(msg => {
            addMessageToDOM(msg.content, msg.role, msg.meta, false);
        });
    }
    
    scrollToBottom();
}

function renderTabs() {
    DOM.tabsContainer.innerHTML = '';
    
    STATE.sessions.forEach(session => {
        const pill = document.createElement('div');
        pill.className = `tab-pill ${session.id === STATE.activeSessionId ? 'active' : ''}`;
        pill.innerHTML = `
            <span>${session.title}</span>
            <span class="tab-close"><i class="fas fa-times"></i></span>
        `;
        
        // Switch on click
        pill.addEventListener('click', () => switchSession(session.id));
        
        // Close on X click
        pill.querySelector('.tab-close').addEventListener('click', (e) => closeSession(session.id, e));
        
        DOM.tabsContainer.appendChild(pill);
    });

    // "New Tab" Button
    const addBtn = document.createElement('button');
    addBtn.className = 'btn-new-tab';
    addBtn.innerHTML = '<i class="fas fa-plus"></i>';
    addBtn.title = "New Session";
    addBtn.addEventListener('click', createNewSession);
    DOM.tabsContainer.appendChild(addBtn);
}

// ==================== Actions ====================

async function handleScanClick() {
    if (STATE.isProcessing) return;
    
    const session = getActiveSession();
    await checkCurrentTab(); // Get fresh URL from Chrome
    
    if (!STATE.currentChromeTab?.url) {
        alert("Cannot connect to this page.");
        return;
    }

    STATE.isProcessing = true;
    setOverlay(true, "Connecting...");

    try {
        const url = STATE.currentChromeTab.url;
        const hostname = new URL(url).hostname;

        // Update Session Metadata
        session.url = url;
        session.title = hostname.replace('www.', '').substring(0, 15); // Short title
        session.isConnected = false;
        session.history = []; // Clear history on new scan
        session.analysis = null;
        
        saveSessions();
        renderTabs(); // Update title

        // 1. Index
        const indexRes = await apiRequest('/index', { url: url, max_pages: 3 });
        if (!indexRes.success) throw new Error("Indexing failed");

        // 2. Poll for Analysis
        const analysis = await waitForAnalysis(url);
        
        // 3. Update Session State
        session.isConnected = true;
        session.analysis = parseAnalysis(analysis);
        
        // Add success message with suggested questions
        const suggestedQuestions = [
            'What is this page about?',
            'What are the main topics?',
            'Summarize this page'
        ];
        
        session.history.push({
            role: 'assistant',
            content: `I've successfully indexed **${hostname}**. What would you like to know?`,
            meta: { suggested_questions: suggestedQuestions }
        });

        saveSessions();
        renderUI();

    } catch (e) {
        console.error(e);
        alert(`Connection failed: ${e.message}`);
    } finally {
        STATE.isProcessing = false;
        setOverlay(false);
    }
}

async function handleSendClick() {
    const text = DOM.userInput.value.trim();
    if (!text || STATE.isProcessing) return;
    
    const session = getActiveSession();
    if (!session.isConnected) return;

    STATE.isProcessing = true;
    DOM.userInput.value = '';
    
    // 1. Add User Message
    const userMsg = { role: 'user', content: text };
    session.history.push(userMsg);
    addMessageToDOM(text, 'user', null, true);
    
    // 2. Add Loading Bubble
    const loaderId = addLoaderToDOM();

    try {
        // 3. API Query with timing
        const startTime = Date.now();
        
        const res = await apiRequest('/query', {
            question: text,
            history: session.history,
            url: session.url // IMPORTANT: Scope query to this session's URL
        });

        const responseTime = (Date.now() - startTime) / 1000; // Convert to seconds
        removeLoaderFromDOM(loaderId);

        if (res.success) {
            const meta = {
                sources: res.data.sources || [],
                confidence: res.data.confidence || res.data.confidence_score,
                time: responseTime,
                suggested_questions: res.data.suggested_questions || []
            };
            
            const botMsg = {
                role: 'assistant',
                content: res.data.answer,
                meta: meta
            };
            session.history.push(botMsg);
            addMessageToDOM(botMsg.content, 'assistant', botMsg.meta, true);
        } else {
            addMessageToDOM("Error: " + res.error, 'bot', { isError: true }, true);
        }
        
        saveSessions();

    } catch (e) {
        removeLoaderFromDOM(loaderId);
        addMessageToDOM("Network Error: " + e.message, 'bot', { isError: true }, true);
    } finally {
        STATE.isProcessing = false;
        DOM.userInput.disabled = false;
        DOM.sendBtn.disabled = false;
        scrollToBottom();
    }
}

// ==================== Helpers ====================

async function checkCurrentTab() {
    return new Promise(resolve => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0] && tabs[0].url.startsWith('http')) {
                STATE.currentChromeTab = tabs[0];
            } else {
                STATE.currentChromeTab = null;
            }
            resolve();
        });
    });
}

function addMessageToDOM(text, role, meta, animate) {
    const row = document.createElement('div');
    row.className = `msg-row ${role === 'user' ? 'user' : 'bot'}`;
    
    const bubble = document.createElement('div');
    bubble.className = `msg ${role === 'user' ? 'user' : 'bot'}`;
    
    // Markdown Parsing with proper formatting
    let contentHtml = text;
    if (typeof marked !== 'undefined') {
        contentHtml = marked.parse(text);
    } else {
        // Basic escaping if marked not available
        contentHtml = `<p>${text.replace(/\n/g, '<br>')}</p>`;
    }
    
    bubble.innerHTML = contentHtml;

    // Add metadata for bot messages
    if (role !== 'user' && meta) {
        let metaHtml = '<div class="msg-meta">';
        let hasMetadata = false;

        // Response time
        if (meta.time) {
            metaHtml += `<span class="meta-tag"><i class="fas fa-clock"></i> ${meta.time.toFixed(1)}s</span>`;
            hasMetadata = true;
        }

        // Confidence score
        if (meta.confidence !== undefined) {
            const confScore = typeof meta.confidence === 'number' ? 
                Math.round(meta.confidence * 100) : 
                (meta.confidence === 'high' ? 90 : meta.confidence === 'medium' ? 70 : 50);
            metaHtml += `<span class="meta-tag"><i class="fas fa-lightbulb"></i> ${confScore}%</span>`;
            hasMetadata = true;
        }

        metaHtml += '</div>';
        
        if (hasMetadata) {
            bubble.innerHTML += metaHtml;
        }
    }

    // Add citations/sources with deep linking
    if (meta && meta.sources && meta.sources.length) {
        const sourcesHtml = meta.sources.map((sourceObj, i) => {
            try {
                const url = new URL(sourceObj.url);
                const snippet = sourceObj.snippet || '';
                
                // Construct Chrome Text Fragment URL for deep linking
                let citationUrl = url.href;
                if (snippet) {
                    // Use first 10-15 words of snippet for reliable deep linking
                    const shortSnippet = snippet.split(' ').slice(0, 12).join(' ');
                    const encodedSnippet = encodeURIComponent(shortSnippet);
                    citationUrl = `${url.href}#:~:text=${encodedSnippet}`;
                }
                
                return `<a href="${citationUrl}" target="_blank" title="View source: ${url.hostname}\n\n${snippet}" style="color:var(--accent);text-decoration:underline;font-size:11px;margin-right:8px;font-weight:500;transition:all 0.2s;" onmouseover="this.style.opacity='0.7'" onmouseout="this.style.opacity='1'">[${i+1}]</a>`;
            } catch {
                return `<span style="color:var(--accent);font-size:11px;margin-right:8px;font-weight:500;">[${i+1}]</span>`;
            }
        }).join('');
        bubble.innerHTML += `<div style="margin-top:10px; border-top:1px solid rgba(37,50,86,0.1); padding-top:8px; font-size:11px; color:var(--text-sub);">Sources: ${sourcesHtml}</div>`;
    }

    row.appendChild(bubble);
    DOM.chatArea.appendChild(row);

    // Add suggested questions if available
    if (meta && meta.suggested_questions && meta.suggested_questions.length > 0) {
        const sugRow = document.createElement('div');
        sugRow.className = 'msg-row bot';
        
        const sugContainer = document.createElement('div');
        sugContainer.style.cssText = 'display:flex; flex-wrap:wrap; gap:8px; padding:0 16px; margin-bottom:8px;';
        
        meta.suggested_questions.forEach(q => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip';
            chip.textContent = q;
            chip.style.cssText = `
                background: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(37, 50, 86, 0.15);
                color: var(--accent);
                padding: 8px 16px;
                border-radius: 20px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 500;
                transition: all 0.2s ease;
            `;
            chip.onmouseover = () => {
                chip.style.borderColor = 'var(--accent)';
                chip.style.background = 'rgba(37, 50, 86, 0.08)';
                chip.style.transform = 'translateY(-1px)';
            };
            chip.onmouseout = () => {
                chip.style.borderColor = 'rgba(37, 50, 86, 0.15)';
                chip.style.background = 'rgba(255, 255, 255, 0.6)';
                chip.style.transform = 'translateY(0)';
            };
            chip.onclick = () => {
                DOM.userInput.value = q;
                DOM.userInput.focus();
                handleSendClick();
            };
            sugContainer.appendChild(chip);
        });
        
        sugRow.appendChild(sugContainer);
        DOM.chatArea.appendChild(sugRow);
    }

    if (animate) scrollToBottom();
}

function addLoaderToDOM() {
    const id = 'loader-' + Date.now();
    const row = document.createElement('div');
    row.id = id;
    row.className = 'msg-row bot';
    row.innerHTML = `<div class="msg bot" style="font-style:italic; color:#888;">Thinking...</div>`;
    DOM.chatArea.appendChild(row);
    scrollToBottom();
    return id;
}

function removeLoaderFromDOM(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    DOM.chatArea.scrollTo({ top: DOM.chatArea.scrollHeight, behavior: 'smooth' });
}

function setOverlay(show, text) {
    DOM.overlay.className = show ? 'overlay active' : 'overlay';
    DOM.overlayText.textContent = text || 'Processing...';
}

// --- API Helpers ---
async function apiRequest(endpoint, body) {
    try {
        const res = await fetch(CONFIG.API_BASE + endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const data = await res.json();
        return { success: res.ok, data: data, error: data.detail || res.statusText };
    } catch (e) {
        return { success: false, error: e.message };
    }
}

async function waitForAnalysis(url) {
    const start = Date.now();
    while (Date.now() - start < CONFIG.REQUEST_TIMEOUT) {
        const res = await apiRequest('/analyze', { url });
        if (res.success && res.data.type !== 'Empty') return res.data;
        await new Promise(r => setTimeout(r, 2000));
    }
    return { type: 'Web Page', summary: 'Indexed successfully.', topics: [] };
}

function parseAnalysis(data) {
    return {
        type: data.type || 'Web Page',
        summary: data.summary || '',
        topics: data.topics || []
    };
}

function formatSummaryAsBullets(text) {
    if (!text) return '';
    return text.split('. ').map(s => `<li>${s}</li>`).join('');
}

// --- Storage ---
async function loadSessions() {
    const res = await chrome.storage.local.get(['ragex_sessions', 'ragex_active_id']);
    if (res.ragex_sessions) STATE.sessions = res.ragex_sessions;
    if (res.ragex_active_id) STATE.activeSessionId = res.ragex_active_id;
}

async function saveSessions() {
    await chrome.storage.local.set({
        ragex_sessions: STATE.sessions,
        ragex_active_id: STATE.activeSessionId
    });
}

// Start
document.addEventListener('DOMContentLoaded', initialize);
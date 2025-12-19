/**
 * RAGx Companion - Background Service Worker
 * ============================================
 * Handles extension lifecycle and side panel management.
 */

// ==================== Extension Icon Click Handler ====================
// Opens side panel when user clicks extension icon in toolbar
chrome.action.onClicked.addListener(async (tab) => {
  try {
    // Open side panel for this window
    await chrome.sidePanel.open({ windowId: tab.windowId });
    
    // Log for debugging (visible in service worker console)
    console.log('[RAGx] Side panel opened for tab:', tab.id);
    
  } catch (error) {
    console.error('[RAGx] Failed to open side panel:', error);
  }
});

// ==================== Extension Installation Handler ====================
// Runs once when extension is first installed or updated
chrome.runtime.onInstalled.addListener((details) => {
  const { reason, previousVersion } = details;
  
  if (reason === 'install') {
    console.log('[RAGx] Extension installed successfully');
    
    // Set default settings on first install
    chrome.storage.local.set({
      apiBase: 'http://127.0.0.1:8000/api/v1',
      maxPages: 3,
      sessionHistory: []
    });
    
  } else if (reason === 'update') {
    console.log(`[RAGx] Extension updated from ${previousVersion} to ${chrome.runtime.getManifest().version}`);
  }
});

// ==================== Message Handler ====================
// Listens for messages from side panel or content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[RAGx] Received message:', message.type);
  
  // Handle different message types
  switch (message.type) {
    case 'GET_CURRENT_TAB':
      // Get active tab information
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]) {
          sendResponse({
            success: true,
            tab: {
              id: tabs[0].id,
              url: tabs[0].url,
              title: tabs[0].title
            }
          });
        } else {
          sendResponse({ success: false, error: 'No active tab' });
        }
      });
      return true; // Keep channel open for async response
      
    case 'PING':
      // Health check
      sendResponse({ success: true, message: 'pong' });
      return true;
      
    default:
      console.warn('[RAGx] Unknown message type:', message.type);
      sendResponse({ success: false, error: 'Unknown message type' });
  }
});

// ==================== Error Handler ====================
// Global error handler for service worker
self.addEventListener('error', (event) => {
  console.error('[RAGx] Service worker error:', event.error);
});

// ==================== Keep Service Worker Alive ====================
// Chrome may shut down service workers after 30 seconds of inactivity
// This periodic task keeps it alive if needed
const KEEPALIVE_INTERVAL = 25000; // 25 seconds

setInterval(() => {
  // Perform lightweight task to keep worker alive
  chrome.storage.local.get(['lastActivity'], (result) => {
    const now = Date.now();
    const lastActivity = result.lastActivity || 0;
    
    // Only log if there was recent activity (within 5 minutes)
    if (now - lastActivity < 300000) {
      console.log('[RAGx] Service worker keepalive ping');
    }
  });
}, KEEPALIVE_INTERVAL);

console.log('[RAGx] Background service worker initialized');
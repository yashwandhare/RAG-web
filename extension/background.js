/**
 * RAGex Companion - Background Service Worker
 * ============================================
 * Handles extension lifecycle and side panel management.
 */

// ==================== Extension Installation Handler ====================
// Runs once when extension is first installed or updated
chrome.runtime.onInstalled.addListener((details) => {
  const { reason, previousVersion } = details;
  
  if (reason === 'install') {
    console.log('[RAGex] Extension installed successfully');
    
    // Set default settings on first install
    chrome.storage.local.set({
      apiBase: 'http://127.0.0.1:8000/api/v1',
      maxPages: 3,
      sessionHistory: []
    });
    
  } else if (reason === 'update') {
    console.log(`[RAGex] Extension updated from ${previousVersion} to ${chrome.runtime.getManifest().version}`);
  }
});

// ==================== Extension Icon Click Handler ====================
// Opens the side panel when user clicks the extension icon
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});

// ==================== Message Handler ====================
// Listens for messages from side panel or content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[RAGex] Received message:', message.type);
  
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
      console.warn('[RAGex] Unknown message type:', message.type);
      sendResponse({ success: false, error: 'Unknown message type' });
  }
});

// ==================== Error Handler ====================
// Global error handler for service worker
self.addEventListener('error', (event) => {
  console.error('[RAGex] Service worker error:', event.error);
});

console.log('[RAGex] Background service worker initialized');
// src/frontend/extension/background.js

const ALLOWED_ORIGINS = [
  'https://alislam.org',
  'https://www.alislam.org',
  'chrome://extensions',
  'about:debugging'
];

let isSidePanelOpen = false;

function isAllowed(url) {
  if (!url) return false;
  return ALLOWED_ORIGINS.some(origin => url.startsWith(origin));
}

// Chrome side panel behavior: open on click
if (typeof chrome !== 'undefined' && chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error(error));
}

// Firefox: Use action.onClicked to toggle the sidebar
// We must call open/close synchronously in the handler to satisfy "user input handler" requirement
if (typeof browser !== 'undefined' && browser.sidebarAction) {
  chrome.action.onClicked.addListener((tab) => {
    console.log("Action clicked in Firefox. Current known state:", isSidePanelOpen);
    if (isSidePanelOpen) {
      browser.sidebarAction.close();
    } else {
      browser.sidebarAction.open();
    }
  });
}

// State management
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'quranai-sidepanel') {
    console.log("Sidepanel connected");
    isSidePanelOpen = true;
    chrome.storage.local.set({ isSidePanelOpen: true });
    broadcastSidePanelState(true);
    
    port.onDisconnect.addListener(() => {
      console.log("Sidepanel disconnected");
      isSidePanelOpen = false;
      chrome.storage.local.set({ isSidePanelOpen: false });
      broadcastSidePanelState(false);
    });
  }
});

async function broadcastSidePanelState(isOpen) {
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    if (tab.id) {
      chrome.tabs.sendMessage(tab.id, { action: 'sidepanel_state_changed', isOpen }).catch(() => {
        // Expected if content script is not injected
      });
    }
  }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'get_sidepanel_state') {
    chrome.storage.local.get(['isSidePanelOpen'], (result) => {
      sendResponse({ isOpen: result.isSidePanelOpen || isSidePanelOpen });
    });
    return true; 
  }
});

// Tab status management
async function updateActionState(tabId, url) {
  if (isAllowed(url)) {
    await chrome.action.enable(tabId);
  } else {
    await chrome.action.disable(tabId);
  }
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' || changeInfo.url) {
    updateActionState(tabId, tab.url);
  }
});

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  updateActionState(activeInfo.tabId, tab.url);
});

chrome.runtime.onInstalled.addListener(async () => {
  chrome.storage.local.set({ isSidePanelOpen: false });
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    updateActionState(tab.id, tab.url);
  }
});

console.log("QuranAI background script initialized.");

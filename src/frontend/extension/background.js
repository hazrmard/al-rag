// src/frontend/extension/background.js

const ALLOWED_ORIGINS = [
  'https://alislam.org',
  'https://www.alislam.org',
  'chrome://extensions',
  'about:debugging'
];

function isAllowed(url) {
  if (!url) return false;
  return ALLOWED_ORIGINS.some(origin => url.startsWith(origin));
}

// Function to update the action (icon) state
async function updateActionState(tabId, url) {
  if (isAllowed(url)) {
    await chrome.action.enable(tabId);
  } else {
    await chrome.action.disable(tabId);
  }
}

// Chrome-specific: Enable opening the side panel on extension icon click
if (typeof chrome !== 'undefined' && chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error(error));
}

// Listener for tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' || changeInfo.url) {
    updateActionState(tabId, tab.url);
  }
});

// Listener for tab activation
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  updateActionState(activeInfo.tabId, tab.url);
});

// Initialize action state on start
chrome.runtime.onInstalled.addListener(async () => {
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    updateActionState(tab.id, tab.url);
  }
});

console.log("QuranAI background script initialized with domain restrictions.");

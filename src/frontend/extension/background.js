// src/frontend/extension/background.js

// Chrome-specific: Enable opening the side panel on extension icon click
if (typeof chrome !== 'undefined' && chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error(error));
}

// In Firefox, the sidebar opens automatically if 'sidebar_action' is defined in manifest.json
// and no popup is set for the 'action' key.

console.log("QuranAI background script initialized.");

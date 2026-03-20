// src/frontend/extension/background.js

let isSidePanelOpen = false;

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

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ isSidePanelOpen: false });
});

console.log("QuranAI background script initialized.");

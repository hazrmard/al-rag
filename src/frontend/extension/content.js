// src/frontend/extension/content.js
console.log("QuranAI content script loaded - v4");

const SVG_ADD = `<svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeLarge" focusable="false" aria-hidden="true" viewBox="0 0 24 24" style="width: 24px; height: 24px; fill: #1976d2;"><path d="M13 7h-2v4H7v2h4v4h2v-4h4v-2h-4V7zm-1-5C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"></path></svg>`;
const SVG_EXPLAIN = `<svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeLarge" focusable="false" aria-hidden="true" viewBox="0 0 24 24" style="width: 24px; height: 24px; fill: #1976d2;"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-8 14l-4-4 1.41-1.41L11 14.17l6.59-6.59L19 9l-8 8z"></path></svg>`;

let isSidePanelOpen = false;

// Request initial state
chrome.runtime.sendMessage({ action: 'get_sidepanel_state' }, (response) => {
  if (response && typeof response.isOpen !== 'undefined') {
    isSidePanelOpen = response.isOpen;
    updateVisibility();
  }
});

// Listen for state changes
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'sidepanel_state_changed') {
    isSidePanelOpen = request.isOpen;
    updateVisibility();
  }
});

function updateVisibility() {
  if (isSidePanelOpen) {
    injectIcons();
  } else {
    removeIcons();
  }
}

function removeIcons() {
  const injected = document.querySelectorAll('.quranai-injected-item');
  injected.forEach(el => el.remove());
  
  // Reset the injected flag on containers so they can be re-injected when panel opens
  const containers = document.querySelectorAll('[data-quranai-injected]');
  containers.forEach(el => {
    delete el.dataset.quranaiInjected;
  });
}

function injectIcons() {
  if (!isSidePanelOpen) return;

  // Target chips that look like verse references (e.g., "1:1")
  const chips = document.querySelectorAll('.MuiChip-root');
  
  chips.forEach(chip => {
    const text = chip.innerText.trim();
    if (/^\d+:\d+$/.test(text)) {
      // Avoid sticky footer/player references
      if (chip.closest('.MuiAppBar-root') || chip.closest('header')) return;

      // Find the verse container
      const container = chip.closest('.MuiPaper-root');
      if (!container) return;

      // Check if we've already injected into this container
      if (container.dataset.quranaiInjected) return;
      container.dataset.quranaiInjected = 'true';

      // The toolbar is the grid containing recitation/download/share icons
      const toolbar = chip.closest('.MuiGrid-container');
      if (toolbar) {
        injectToToolbar(toolbar, text);
      }
    }
  });
}

function injectToToolbar(toolbar, verse) {
  const gridItem = document.createElement('div');
  gridItem.className = 'quranai-injected-item';
  gridItem.style.display = 'inline-flex';
  gridItem.style.alignItems = 'center';
  gridItem.style.gap = '4px';
  gridItem.style.marginLeft = '12px';
  gridItem.style.paddingLeft = '12px';
  gridItem.style.borderLeft = '1px solid rgba(0, 0, 0, 0.12)';
  gridItem.style.height = '32px';

  const btnAdd = createIconButton(SVG_ADD, 'Add to context', () => {
    chrome.runtime.sendMessage({ action: 'add_to_context', verse });
  });

  const btnExplain = createIconButton(SVG_EXPLAIN, 'Explain this verse', () => {
    chrome.runtime.sendMessage({ action: 'explain_verse', verse });
  });

  gridItem.appendChild(btnAdd);
  gridItem.appendChild(btnExplain);

  toolbar.appendChild(gridItem);
}

function createIconButton(svgHtml, title, onClick) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'MuiButtonBase-root MuiIconButton-root MuiIconButton-sizeLarge';
  btn.innerHTML = svgHtml;
  btn.title = title;
  btn.style.cursor = 'pointer';
  btn.style.padding = '4px';
  btn.style.border = 'none';
  btn.style.background = 'none';
  btn.style.transition = 'background-color 0.2s';
  btn.style.borderRadius = '50%';
  btn.style.display = 'flex';
  btn.style.alignItems = 'center';
  btn.style.justifyContent = 'center';
  
  btn.onmouseover = () => { btn.style.backgroundColor = 'rgba(25, 118, 210, 0.08)'; };
  btn.onmouseout = () => { btn.style.backgroundColor = 'transparent'; };
  
  btn.onclick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    onClick();
  };
  
  return btn;
}

// Use MutationObserver for a more responsive injection
const observer = new MutationObserver((mutations) => {
  if (isSidePanelOpen) {
    injectIcons();
  }
});

observer.observe(document.body, {
  childList: true,
  subtree: true
});

// Initial run
updateVisibility();

// Periodic check
setInterval(() => {
  if (isSidePanelOpen) injectIcons();
}, 2000);

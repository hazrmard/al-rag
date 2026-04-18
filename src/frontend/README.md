# QuranAI Frontend

This directory contains the frontend components for the QuranAI project, built with Svelte and bundled using Rollup.

## Structure

- **`shared/`**: Common libraries and utilities.
  - `lib.js`: JavaScript library for interacting with the QuranAI API.
- **`ui/`**: Shared UI components.
  - `App.svelte`: The main Svelte application component shared by both the extension and the web app.
- **`extension/`**: Browser extension implementation.
  - `content.js`: Content script injected into `alislam.org/quran/app` to provide verse-level interactions.
  - `background.js`: Background script managing extension state and cross-browser sidebar toggling.
  - Mounts the shared Svelte app for use in a browser sidebar or side panel.
- **`app/`**: Standalone web application.
  - Mounts the shared Svelte app for a traditional web browser experience.

## Features

- **Verse Context**: Select multiple verses from the page to include as context for your questions.
- **Quick Explain**: One-click icon to instantly ask the agent to explain a specific verse.
- **Shared UI**: Consistent chat experience across the web app and extension sidebar.
- **Cross-Browser State Sync**: In-page icons (➕/💡) automatically appear when the sidebar is open and disappear when it's closed, ensuring a clean reading experience.

## Extension Architecture & State Sync

The extension uses a multi-layered approach to stay in sync across different browsers (Chrome and Firefox):

1. **Heartbeat Connection**: When `App.svelte` mounts in the sidebar, it opens a persistent `runtime.connect` port to the background script.
2. **State Tracking**: `background.js` uses this port connection to track if the sidebar is currently visible.
3. **State Broadcasting**: The background script broadcasts state changes to all active tabs.
4. **Content Script Reactivity**: `content.js` listens for these changes to inject or remove icons from the DOM dynamically using a `MutationObserver`.
5. **Firefox Toggle**: Due to Firefox's security model, the sidebar toggle (via the extension icon) is handled synchronously in the background script using the tracked state.

## Development

Build scripts and dependencies are managed in the root `package.json`.

To build both targets:

```bash
npm run build
```

To start development mode with live reloading:

```bash
npm run dev
```

### Packaging for Review

To package the extension source code for browser extension review (e.g., for the Chrome Web Store or Firefox Add-ons), run the following script from the project root:

```bash
./build_ext_source.sh
```

This will create a `quranai-ext-source.zip` file containing all necessary source files and configuration, excluding build artifacts and dependencies.

# QuranAI Frontend

This directory contains the frontend components for the QuranAI project, built with Svelte and bundled using Rollup.

## Structure

- **`shared/`**: Common libraries and utilities.
  - `lib.js`: JavaScript library for interacting with the QuranAI API.
- **`ui/`**: Shared UI components.
  - `App.svelte`: The main Svelte application component shared by both the extension and the web app.
- **`extension/`**: Browser extension implementation.
  - Mounts the shared Svelte app for use in a browser sidebar or side panel.
- **`app/`**: Standalone web application.
  - Mounts the shared Svelte app for a traditional web browser experience.

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

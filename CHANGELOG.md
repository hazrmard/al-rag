# Changelog

## 0.2.0 — 2026-04-25

- Backend-only split: removed the embedded Svelte web UI and Firefox/Chrome extension. The web UI now lives in the sibling project [`../ask-quran-react/`](../ask-quran-react/) (Vite + React 19 + TypeScript + MUI 9).
  - Removed: `src/frontend/`, `rollup.config.mjs`, `package.json`, `package-lock.json`, `build_ext_package.sh`, `build_ext_source.sh`.
  - Updated: `Dockerfile` (single-stage Python only), `docker-compose.yaml` (only `api-dev` and `api-prod` services), `.env-TEMPLATE` (dropped `QURANAI_API_BASE_URL` and `QURANAI_UI_PORT`), `.gitignore`, `README.md`, `AGENTS.md`.
  - Deferred: re-port of the Firefox / Chrome extension to React, MCP server, CLI entry point.
  - See [`docs/svelte-to-react-split.md`](docs/svelte-to-react-split.md) for the full notes.
- Added `quranai/ui_status.py` — canonical user-facing status strings for the chat loading indicator. Defines `DEFAULT_LOADING_MESSAGE` ("Searching in the Holy Quran and commentaries") and a `TOOL_STATUS_MESSAGES` map keyed by agent tool names. The sibling React UI mirrors these strings; this module is the single source of truth so per-tool progress messages stay consistent if/when the UI switches to streaming via `/run_sse`.
- Updated the root agent instruction to require verse references in `[chapter:verse]` form (e.g. `[1:2]`). The React UI uses this exact format to render inline verse previews; bare `1:2` and other variants are no longer accepted.

## 0.1.0

- Initial backend release with the ADK API server, AI agent, and embedded Svelte web UI.

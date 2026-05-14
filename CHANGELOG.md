# Changelog

## 0.3.0

- Added hadith lookup tool to main Quran agent. The tool makes calls to readquran API to get references and content of related hadith.
- Added READ_QURAN_API_URL env variable to template and run_instances.sh

## 0.2.2

- Fixed "Session not found" errors caused by 5 replicas each writing to their own per-container SQLite at `/app/.../session.db`. The Dockerfile now starts the ADK API with `--session_service_uri 'sqlite:////data/sessions.db'`, and `run-instances.sh` mounts a shared docker named volume `ask-quran-adk-sessions` at `/data` on every replica. All instances now read/write one SQLite file, so nginx round-robin no longer drops sessions.
- Removed `--auto_create_session` from the Dockerfile CMD: in ADK 1.25.1 it is a no-op for `/run`/`/run_sse`/`/run_live` because those endpoints `get_session` and 404 before the runner (where the flag applies) is ever called. The FE handles stale ids with an explicit retry path instead. See `docs/deployment-setup.md` for the longer note.
- `deploy.sh` now ships the local `.env` to the server on first deploy (only when `~/ask-quran-adk/.env` does not already exist), with mode 600. This eliminates the manual paste-and-edit step on `nano`, which previously truncated `GOOGLE_API_KEY` at the `-` character and made every `/run` call return 500. Subsequent deploys leave the server `.env` untouched so any rotated keys or per-server overrides survive.
- Aligned Python version across dev and prod: bumped `.python-version` from `3.11` → `3.13` and `pyproject.toml` `requires-python` from `>=3.11` → `>=3.13` to match the `python:3.13-slim-trixie` Dockerfile base. Previously the Dockerfile resolved deps for 3.13 while local `uv sync` could resolve them for 3.11, risking version skew where a new dependency could install locally but break the Docker build. `uv.lock` regenerated on 3.13.

## 0.2.1 — 2026-04-29

- Added production deployment scripts (`deploy.sh`, `run-instances.sh`) and nginx config (`nginx/ask-api.readquran.app.conf`) for serving the ADK backend at `ask-api.readquran.app` via 5 docker instances on host ports 7991–7995. Set the dev/internal container port to 7990, added a default `CMD` to the `Dockerfile` so `docker run` works without compose, and created a `ask-quran-net` docker network. See `docs/deployment-setup.md` for the full setup notes.
- Bumped Docker base image from `python:3.11-slim` to `python:3.13-slim` to pull in current OS-level security patches (resolves the 2 high CVEs flagged on the older slim image).
- Added `deploy-nginx.sh` — one-shot script that scp's `nginx/ask-api.readquran.app.conf` to the server, installs it under `sites-available` + `sites-enabled`, runs `nginx -t`, and reloads. Mirrors the `yarn deploy:nginx` pattern used in sibling Node projects.

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

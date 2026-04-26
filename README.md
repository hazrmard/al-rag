# QuranAI

A LLM-powered application for conversational research with the Quran.

This repository hosts the **backend**:

1. The core AI agent library (`src/quranai/`)
2. An ADK API server
3. (Planned) An MCP server
4. (Planned) A CLI

The **web UI** lives in a sibling project: [`../ask-quran-react/`](../ask-quran-react/) (Vite + React + MUI).

## Installation

Use [`uv`](https://github.com/astral-sh/uv) for Python dependency management.

```bash
uv sync
```

Copy `.env-TEMPLATE` to `.env` and fill in `GOOGLE_API_KEY`.

## Development & Testing

To run the debug ADK web interface (development convenience):

```bash
uv run adk web --allow_origins "*" --log_level DEBUG src/quranai/agents/
```

To run the API server that the React app talks to:

```bash
./run_api.sh
# or
uv run adk api_server src/quranai/agents/ --allow_origins "*" --port $QURANAI_API_PORT
```

The API server's Swagger UI is available at `http://localhost:$QURANAI_API_PORT/doc`.

`src/scripts/` defines utility scripts to build indices and other workflows not part of runtime. Run them using:

```bash
uv run src/scripts/...
```

## Tests

Python tests live under `src/tests/` and run with `pytest`:

```bash
uv run pytest
```

## Deployment

### Docker (recommended)

The image runs the ADK API server only. The React UI is deployed separately from `../ask-quran-react/`.

1. **Configure environment**: copy `.env-TEMPLATE` to `.env` and fill in `GOOGLE_API_KEY`.
2. **Run (development)**:

```bash
./run_docker_staging.sh
# or
docker compose --profile dev up --build
```

3. **Run (production)**:

```bash
./run_docker_prod.sh
# or
docker compose --profile prod up --build -d
```

4. **Access**: API server at `http://localhost:7999` (or whatever `QURANAI_API_PORT` is set to).

## Web UI

See [`../ask-quran-react/README.md`](../ask-quran-react/README.md) for installing and running the chat interface that consumes this API.

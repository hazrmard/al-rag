# QuranAI

A LLM-powered application for conversational research with the Quran.

This repository hosts the **backend**:

1. The core AI agent library (`src/quranai/`)
2. An ADK API server

The **web UI** lives in a sibling project: [`../ask-quran-react/`](../ask-quran-react/) (Vite + React + MUI).

## Installation

Use [`uv`](https://github.com/astral-sh/uv) for Python dependency management.

```bash
uv sync
```

Copy `.env-TEMPLATE` to `.env` and fill in `GOOGLE_API_KEY`.

### Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `GOOGLE_API_KEY` | *(required)* | Gemini API key for ADK agent reasoning and embeddings. |
| `QURANAI_API_PORT` | `7990` | Port for the ADK API server. |
| `ENABLE_HADITH_TOOLS` | `true` | Enable Hadith retrieval and cross-referencing tools in the agent (`1`/`true`/`yes`). Set to `0` or `false` to disable. |
| `READ_QURAN_API_URL` | `https://api.readquran.app` | Base URL for the Quran API (corpus chapter extraction and online Hadith cross-reference fallback). |
| `QURANAI_DATA_DIR` | `src/quranai/data` | Directory where corpus JSON files (`quran.json`, `hadith.json`) and ChromaDB (`quranai.chroma`) are read and written. |
| `QURANAI_DATA_HOST_DIR` | `./src/quranai/data` | Host directory baked into Docker images via `docker compose` or `deploy.sh`. |
| `QURANAI_CONTAINER_DATA_DIR` | `/app/data` | Target corpus path inside the Docker container (kept separate from `/data`, which stores ADK `sessions.db`). |

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

#### Building with an external corpus directory

To bake corpora stored outside the git repository into the Docker image:

```bash
# Direct docker build (BuildKit)
docker build --build-context data=/path/to/corpora -t ask-quran-adk:latest .

# docker compose
QURANAI_DATA_HOST_DIR=/path/to/corpora docker compose --profile dev up --build

# Production deploy script
./deploy.sh --data-dir /path/to/corpora
```

Inside the container, `QURANAI_DATA_DIR` defaults to `/app/data` (configurable at build time via `--build-arg QURANAI_DATA_DIR=...` or overridden at runtime with `-v /host/corpora:/opt/corpora -e QURANAI_DATA_DIR=/opt/corpora`).

## Web UI

See [`../ask-quran-react/README.md`](../ask-quran-react/README.md) for installing and running the chat interface that consumes this API.

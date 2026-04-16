# QuranAI

A LLM-powered application for conversational research with Quran.

This application exposes:

1. A web interface
2. A MCP server
3. A CLI
4. The core agent library

To interact with the corpus.

## Installation

## Development & Testing

To run the debug web interface for the LLM agent (development):

```bash
uv run adk web --allow_origins "*" --log_level DEBUG --port 7999 src/quranai/agents/
```

To run the web app interface:

```bash
npm run dev
python3 -m http.server -d public/app
```

To run the API server (with CORS enabled for the browser extension):

```bash
./run_api.sh
```

Alternatively, run manually for the API server:

```bash
uv run adk api_server src/quranai/agents/ --allow_origins "*"
```

> **Note on CORS:** Browser extensions require CORS headers from the API server (especially when calling from the sidebar). If you get a `405 Method Not Allowed` or `CORS header ‘Access-Control-Allow-Origin’ missing` error, ensure the `--allow_origins` flag is set correctly.

`src/scripts/` defines utility scripts to build indices and other workflows not part of runtime. Run them using:

```bash
uv run src/scripts/...
```

## Deployment

### Docker (Recommended)

The easiest way to run the entire stack (API + Web App) is using Docker Compose.

1. **Configure Environment**: Copy `.env-TEMPLATE` to `.env` and fill in your `GOOGLE_API_KEY`.
2. **Build and Run**:

```bash
docker-compose up --build
```

3. **Access**:
    - Web App: [http://localhost:7998](http://localhost:7998)
    - API Server: [http://localhost:7999](http://localhost:7999)

### Extension

The extension makes calls to the API server. To deploy server-side, run the api server command.

#### Packaging for Distribution

To build and package the extension for the Chrome Web Store or Firefox Add-ons:

```bash
./build_ext_package.sh
```

This will create `quranai-extension.zip` in the root directory.

To package the source code for review (as required by some stores):

```bash
./build_ext_source.sh
```

This will create `quranai-ext-source.zip` in the root directory.


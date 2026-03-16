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

To run the web interface:

```
uv run adk web --log_level DEBUG --port 8000 src/quranai/agents/
```

To run the API server:

```
adk api_server src/quranai/agents/
```

`src/scripts/` defines utility scripts to build indices and other workflows not part of runtime. Run them using:

```
uv run src/scripts/...
```

## Deployment


### Extension

The extension makes calls to the API server. To deploy server-side, run the api server command.


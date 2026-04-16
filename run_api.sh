#!/bin/bash

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Use values from .env or fall back to defaults
PORT=${QURANAI_API_PORT:-7999}
ALLOW_ORIGINS="*"

echo "Starting API server on port $PORT with CORS enabled for: $ALLOW_ORIGINS"

uv run adk api_server src/quranai/agents/ --allow_origins "$ALLOW_ORIGINS" --port "$PORT"

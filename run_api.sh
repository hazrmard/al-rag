#!/bin/bash

# Script to run the QuranAI API server with CORS enabled for the browser extension.
# Using "*" for development allows the extension to connect from its local origin.

# For production, replace "*" with specific origins like "https://alislam.org"
ALLOW_ORIGINS="*"

echo "Starting API server with CORS enabled for: $ALLOW_ORIGINS"

uv run adk api_server src/quranai/agents/ --allow_origins "$ALLOW_ORIGINS" --port 8000Keep

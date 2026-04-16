# Stage 1: Build the frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy package files for better caching
COPY package.json package-lock.json ./
RUN npm install --silent

# Copy the rest of the frontend source
COPY . .

# Build the frontend artifacts to public/
# The API base URL must be accessible from the user's browser.
# We use an ARG so it can be overridden at build time.
ARG QURANAI_API_BASE_URL
ENV QURANAI_API_BASE_URL=${QURANAI_API_BASE_URL}

RUN npm run build

# Stage 2: Final runtime image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/app/.venv/bin:/uv/bin:${PATH}"
ENV UV_LINK_MODE=copy

# Install python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy built frontend artifacts from stage 1
COPY --from=frontend-builder /app/public/app ./public/app

# Copy the backend source and other necessary files
COPY src/ ./src/
RUN touch ./README.md
# Sync the project itself (now that src is present)
RUN uv sync --frozen --no-dev

# No default CMD or start.sh; these will be provided in docker-compose.yaml

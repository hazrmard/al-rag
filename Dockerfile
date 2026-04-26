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

# Copy the backend source
COPY src/quranai ./src/quranai
RUN touch ./README.md
RUN uv sync --frozen --no-dev

# No default CMD; provided by docker-compose.yaml

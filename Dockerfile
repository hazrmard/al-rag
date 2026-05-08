FROM python:3.13-slim-trixie

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

# Shared session storage mount point. run-instances.sh mounts a named volume
# here so all replicas read/write the same SQLite file.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 7990

# Default CMD — used by `docker run` (run-instances.sh in production).
# docker-compose overrides this with its own `command:` for dev/prod profiles.
CMD ["sh", "-c", "uv run adk api_server src/quranai/agents/ --host 0.0.0.0 --port ${QURANAI_API_PORT:-7990} --allow_origins '*' --session_service_uri 'sqlite:////data/sessions.db'"]

# syntax=docker/dockerfile:1

# Default corpus data stage. Override with `--build-context data=/path/to/corpora`
# to bake corpora from an external host directory outside this repo, or
# `--build-arg DATA_SRC=<relative-dir>` for another directory inside the repo.
ARG DATA_SRC=src/quranai/data

FROM scratch AS data
ARG DATA_SRC
COPY ${DATA_SRC} /

# Strip bundled src/quranai/data from the source tree so the final image does not
# duplicate corpus files (or bake stale in-repo data when overriding `data`).
FROM python:3.13-slim-trixie AS src-prep
COPY src/quranai /src/quranai
RUN rm -rf /src/quranai/data && mkdir -p /src/quranai/data

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

# Copy corpus data into QURANAI_DATA_DIR (kept separate from /data used for sessions.db).
# Declared after dependency install so changing QURANAI_DATA_DIR keeps apt/uv layers cached,
# and before source copy so code-only edits reuse the cached data layer.
ARG QURANAI_DATA_DIR=/app/data
ENV QURANAI_DATA_DIR=${QURANAI_DATA_DIR}
COPY --from=data / ${QURANAI_DATA_DIR}

# Copy the backend source (without bundled data) and install the package
COPY --from=src-prep /src/quranai ./src/quranai
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

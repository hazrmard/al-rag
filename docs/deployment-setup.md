# Production Deployment Setup

This document describes how the `ask-quran-adk` backend is deployed to the
shared production server. It mirrors the pattern used by `hadith-express` —
the BE runs as 5 docker instances behind nginx, with domain-based routing.

## Topology

| Item                      | Value                                              |
| ------------------------- | -------------------------------------------------- |
| Server                    | `almalinux@148.113.226.32` (256 GB RAM, 1 TB disk) |
| Public domain             | `ask-api.readquran.app`                            |
| DNS provider              | Cloudflare (proxied; nginx serves plain HTTP)      |
| Server install path       | `~/ask-quran-adk/`                                 |
| Docker image              | `ask-quran-adk:latest` (with `:previous` rollback) |
| Docker network            | `ask-quran-net`                                    |
| Number of instances       | 5                                                  |
| Host ports                | `7991`–`7995`                                      |
| Container internal port   | `7990` (matches dev port)                          |
| Dev port (docker-compose) | `7990`                                             |
| Session storage           | Shared docker named volume `ask-quran-adk-sessions` mounted at `/data`; one SQLite file (`/data/sessions.db`) across all replicas |
| Health endpoint           | `/health` (provided by ADK out of the box)         |
| Version endpoint          | `/version` (provided by ADK)                       |

The frontend (React) lives in the sibling `ask-quran-react` project and is
deployed separately; it is **not** managed by these scripts.

## Files in this repo

| File                                     | Purpose                                                                |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| `deploy.sh`                              | Build the docker image locally, ship it to the server, and load it.    |
| `run-instances.sh`                       | Manage 5 instances on the server (start/stop/update/rollback/status).  |
| `nginx/ask-api.readquran.app.conf`       | Nginx upstream + server block for the public domain.                   |
| `nginx/README.md`                        | Steps to install the nginx config on the server.                       |
| `Dockerfile`                             | Adds a default `CMD` so `docker run` (no compose) starts the API.      |
| `docker-compose.yaml`                    | Dev/prod profiles, default port now `7990`.                            |
| `.env-TEMPLATE` / `.env`                 | `QURANAI_API_PORT` defaults to `7990`.                                 |

## First-time deploy

1. **DNS** — point `ask-api.readquran.app` (A record) at `148.113.226.32` in
   Cloudflare. Proxied (orange cloud) is fine.

2. **Push image and run-instances.sh** from your laptop:

   ```bash
   ./deploy.sh
   ```

   This builds for `linux/amd64`, scps a gzipped tar to the server, loads it
   into docker, and creates a placeholder `~/ask-quran-adk/.env` if one does
   not already exist.

3. **Set GOOGLE_API_KEY** on the server (the placeholder `.env` ships with an
   empty key):

   ```bash
   ssh almalinux@148.113.226.32
   nano ~/ask-quran-adk/.env
   ```

4. **Start the 5 instances**:

   ```bash
   cd ~/ask-quran-adk
   ./run-instances.sh start
   ./run-instances.sh status
   ```

5. **Install the nginx config** (one-time, see `nginx/README.md`):

   ```bash
   # from your laptop
   scp nginx/ask-api.readquran.app.conf almalinux@148.113.226.32:/tmp/

   # on the server
   sudo mv /tmp/ask-api.readquran.app.conf /etc/nginx/sites-available/
   sudo ln -sf /etc/nginx/sites-available/ask-api.readquran.app.conf \
               /etc/nginx/sites-enabled/ask-api.readquran.app.conf
   sudo nginx -t && sudo systemctl reload nginx
   ```

## Subsequent deploys

```bash
./deploy.sh                          # ship new image
ssh almalinux@148.113.226.32
cd ~/ask-quran-adk
./run-instances.sh update            # zero-downtime rolling update
```

The previous image is automatically tagged `ask-quran-adk:previous` before
the new image is loaded, so you can roll back with:

```bash
./run-instances.sh rollback
```

## Why sessions need shared storage

ADK's default session service writes to a per-agent SQLite file inside the
container's filesystem. With 5 replicas behind nginx round-robin, a session
created on instance #2 is unreachable from instance #5 — every other request
in a chat would hit "Session not found".

The Dockerfile starts the API with:

```
--session_service_uri 'sqlite:////data/sessions.db'
```

`run-instances.sh` mounts the docker named volume `ask-quran-adk-sessions` at
`/data` on every replica, so all 5 share one SQLite file. SQLite's WAL mode
handles the (low) concurrent-write load fine for chat traffic. If you ever
outgrow it, swap the URI for a `postgresql://...` one and point at a managed
DB — no other code changes needed.

> Note: ADK 1.25.1 also exposes a `--auto_create_session` flag, but as of
> that version it is a no-op for `/run` (and `/run_sse`, `/run_live`):
> `adk_web_server.py` performs its own `get_session` check and 404s before
> the runner — where the flag actually applies — is ever invoked.
> The FE compensates with an explicit `POST /sessions` before `/run` and a
> catch-and-retry on 404 to handle stale `localStorage` ids.

## Why the container internal port is 7990

The ADK API server is started inside the container with
`--port ${QURANAI_API_PORT:-7990}`. Using 7990 inside every container and
mapping host ports `7991:7990` … `7995:7990` keeps the configuration
symmetrical with local dev (`docker compose --profile dev up`, also 7990).

## Health checks

`google-adk` registers a `/health` route on the FastAPI app it builds, so
`run-instances.sh` can probe `http://localhost:<port>/health` after each
container start during a rolling update without any application changes.
`/version` is also available for sanity-checking which image is live.

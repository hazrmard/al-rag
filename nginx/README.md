# Nginx Configuration Guide

## Overview

This directory contains the nginx configuration for the `ask-quran-adk` backend.
The backend is deployed at `ask-api.readquran.app` using domain-based routing on
the shared server. The corresponding React frontend lives in the sibling
`ask-quran-react` project and has its own deployment / nginx config.

## Structure

For multiple apps on the server, use this structure:

```
/etc/nginx/
├── sites-available/
│   ├── ask-api.readquran.app.conf
│   ├── readhadith.app.conf
│   └── ...
└── sites-enabled/
    ├── ask-api.readquran.app.conf -> ../sites-available/ask-api.readquran.app.conf
    ├── readhadith.app.conf -> ../sites-available/readhadith.app.conf
    └── ...
```

## Setup Instructions

### One-shot script (recommended)

From the repo root:

```bash
./deploy-nginx.sh
```

This scp's the conf to `/tmp/`, moves it into `sites-available/`, symlinks it
into `sites-enabled/`, runs `sudo nginx -t`, then `sudo systemctl reload nginx`.

### Manual fallback

```bash
# 1. Copy file to server temporary directory
scp nginx/ask-api.readquran.app.conf almalinux@148.113.226.32:/tmp/ask-api.readquran.app.conf

# 2. login to the server
ssh almalinux@148.113.226.32

# 3. move the file to sites-available
sudo mv /tmp/ask-api.readquran.app.conf /etc/nginx/sites-available/ask-api.readquran.app.conf

# 4. create a symlink to sites-enabled
sudo ln -sf /etc/nginx/sites-available/ask-api.readquran.app.conf /etc/nginx/sites-enabled/ask-api.readquran.app.conf

# 5. test the configuration
sudo nginx -t

# 6. reload nginx
sudo systemctl reload nginx
```

## Cloudflare DNS

Point `ask-api.readquran.app` to the server IP (`148.113.226.32`) in Cloudflare.
Proxied (orange cloud) is fine; nginx serves plain HTTP on port 80 and
Cloudflare terminates TLS.

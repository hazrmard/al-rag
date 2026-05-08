#!/bin/bash

# Deploys nginx/ask-api.readquran.app.conf to the production server.
# Usage: ./deploy-nginx.sh

set -e

SERVER_USER="almalinux"
SERVER_HOST="148.113.226.32"
CONF_NAME="ask-api.readquran.app.conf"
LOCAL_CONF="nginx/${CONF_NAME}"

if [ ! -f "${LOCAL_CONF}" ]; then
    echo "❌ Cannot find ${LOCAL_CONF} (run from the repo root)."
    exit 1
fi

echo "📤 Uploading ${LOCAL_CONF} to ${SERVER_USER}@${SERVER_HOST}..."
scp "${LOCAL_CONF}" "${SERVER_USER}@${SERVER_HOST}:/tmp/${CONF_NAME}"

echo "🔧 Installing on server (sites-available + sites-enabled, then reload)..."
ssh "${SERVER_USER}@${SERVER_HOST}" "\
    sudo mv /tmp/${CONF_NAME} /etc/nginx/sites-available/${CONF_NAME} && \
    sudo ln -sf /etc/nginx/sites-available/${CONF_NAME} /etc/nginx/sites-enabled/${CONF_NAME} && \
    sudo nginx -t && \
    sudo systemctl reload nginx"

echo "✅ Nginx config deployed and reloaded."

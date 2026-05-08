#!/bin/bash

# Deployment script for ask-quran-adk (Python / google-adk backend)
# Builds Docker image locally and pushes to server
# Usage: ./deploy.sh

set -e

SERVER_USER="almalinux"
SERVER_HOST="148.113.226.32"
SERVER_PATH="~/ask-quran-adk"
IMAGE_NAME="ask-quran-adk:latest"
IMAGE_FILE="ask-quran-adk-image.tar.gz"

echo "🚀 Starting deployment to ${SERVER_USER}@${SERVER_HOST}..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Build Docker image locally for linux/amd64 platform
echo -e "${YELLOW}🔨 Building Docker image locally for linux/amd64...${NC}"
docker build --platform linux/amd64 -t ${IMAGE_NAME} .

# Step 2: Save image to tar file
echo -e "${YELLOW}💾 Saving Docker image...${NC}"
docker save ${IMAGE_NAME} | gzip > ${IMAGE_FILE}

# Step 3: Transfer image and scripts to server
echo -e "${YELLOW}📤 Transferring image and scripts to server...${NC}"
scp ${IMAGE_FILE} ${SERVER_USER}@${SERVER_HOST}:~/

# Ensure directory exists with correct permissions and copy script
echo -e "${YELLOW}📋 Copying run-instances.sh to server...${NC}"
ssh "${SERVER_USER}@${SERVER_HOST}" "mkdir -p ~/ask-quran-adk && chown ${SERVER_USER}:${SERVER_USER} ~/ask-quran-adk 2>/dev/null || true"
if scp run-instances.sh ${SERVER_USER}@${SERVER_HOST}:~/ask-quran-adk/; then
    echo "✅ run-instances.sh copied successfully"
    # Verify it was copied
    ssh "${SERVER_USER}@${SERVER_HOST}" "ls -la ~/ask-quran-adk/run-instances.sh" || {
        echo -e "${RED}❌ File not found after copy, checking permissions...${NC}"
        ssh "${SERVER_USER}@${SERVER_HOST}" "ls -la ~/ask-quran-adk/"
    }
else
    echo -e "${RED}❌ Failed to copy run-instances.sh${NC}"
    exit 1
fi

# Ship the local .env to the server only if no .env exists there yet.
# This avoids overwriting any server-side edits (e.g. rotated keys, custom
# port) on subsequent deploys, but eliminates the manual paste-and-truncate
# step on first deploy.
if [ -f .env ]; then
    echo -e "${YELLOW}🔐 Checking server .env...${NC}"
    if ssh "${SERVER_USER}@${SERVER_HOST}" "[ -f ~/ask-quran-adk/.env ]"; then
        echo "ℹ️  Server already has ~/ask-quran-adk/.env — leaving it as-is."
        echo "    To force-replace, run: scp .env ${SERVER_USER}@${SERVER_HOST}:~/ask-quran-adk/.env"
    else
        echo -e "${YELLOW}📤 Shipping local .env (first-time setup)...${NC}"
        scp .env "${SERVER_USER}@${SERVER_HOST}:~/ask-quran-adk/.env"
        ssh "${SERVER_USER}@${SERVER_HOST}" "chmod 600 ~/ask-quran-adk/.env"
        echo "✅ .env copied (mode 600)"
    fi
else
    echo -e "${YELLOW}⚠️  No local .env found — server will get a placeholder if missing.${NC}"
fi

# Step 4: Load image on server
echo -e "${YELLOW}🚀 Loading image on server...${NC}"
ssh "${SERVER_USER}@${SERVER_HOST}" << ENDSSH
# Check if user needs sudo for docker
if docker ps >/dev/null 2>&1; then
    DOCKER_CMD="docker"
elif sudo docker ps >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
else
    echo "Error: Cannot access Docker. Please ensure Docker is installed and user has permissions."
    exit 1
fi

# Create ask-quran-adk directory if it doesn't exist
mkdir -p ~/ask-quran-adk

# Create .env file if it doesn't exist (you should edit this with real credentials!)
if [ ! -f ~/ask-quran-adk/.env ]; then
    echo "⚠️  Creating placeholder .env file — set GOOGLE_API_KEY before starting instances!"
    cat > ~/ask-quran-adk/.env << EOF
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=
QURANAI_API_PORT=7990
EOF
fi

# Before loading new image, tag the current 'latest' as 'previous' for rollback capability
if \$DOCKER_CMD images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | grep -q "^${IMAGE_NAME}\$" || \
   \$DOCKER_CMD images 2>/dev/null | grep -q "${IMAGE_NAME}"; then
    echo "Tagging current 'latest' as 'previous' for rollback..."
    CURRENT_IMAGE_ID=\$(\$DOCKER_CMD images ${IMAGE_NAME} --format "{{.ID}}" 2>/dev/null | head -n 1)
    if [ ! -z "\$CURRENT_IMAGE_ID" ]; then
        \$DOCKER_CMD tag ${IMAGE_NAME} ask-quran-adk:previous 2>/dev/null || true
        echo "✅ Previous version tagged as 'ask-quran-adk:previous'"
    fi
fi

# Load the new image (Docker will automatically update the 'latest' tag)
echo "Loading new image..."
\$DOCKER_CMD load < ~/${IMAGE_FILE}

# Clean up dangling/untagged images (but keep 'previous' and 'latest')
echo "Cleaning up untagged/dangling images..."
\$DOCKER_CMD image prune -f >/dev/null 2>&1 || true

# Verify image was loaded (try multiple methods for compatibility)
IMAGE_LOADED=false
if \$DOCKER_CMD images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | grep -q "^${IMAGE_NAME}\$"; then
    IMAGE_LOADED=true
elif \$DOCKER_CMD images 2>/dev/null | grep -q "ask-quran-adk"; then
    IMAGE_LOADED=true
fi

if [ "\$IMAGE_LOADED" = "true" ]; then
    echo "✅ Image ${IMAGE_NAME} loaded successfully!"
    echo ""
    echo "Image details:"
    \$DOCKER_CMD images ${IMAGE_NAME} 2>/dev/null | head -2 || \
    \$DOCKER_CMD images 2>/dev/null | grep ask-quran-adk | head -2
else
    echo "⚠️  Warning: Could not verify image was loaded. Please check manually:"
    echo "   \$DOCKER_CMD images | grep ask-quran-adk"
    echo ""
    echo "If the image exists, you can proceed with: ./run-instances.sh start"
fi

# Make run-instances.sh executable
chmod +x ~/ask-quran-adk/run-instances.sh

# Clean up image file on server
rm -f ~/${IMAGE_FILE}

echo ""
echo "To run instances, SSH to the server and run:"
echo "  cd ~/ask-quran-adk"
echo "  ./run-instances.sh start"
ENDSSH

# Clean up local image file
echo -e "${YELLOW}🧹 Cleaning up local files...${NC}"
rm -f ${IMAGE_FILE}

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. SSH to server: ssh ${SERVER_USER}@${SERVER_HOST}"
echo -e "  2. Go to directory: cd ~/ask-quran-adk"
echo -e "  3. Verify .env has a valid GOOGLE_API_KEY"
echo -e "  4. Update instances (zero-downtime): ./run-instances.sh update"
echo ""
echo -e "Available commands:"
echo -e "  ./run-instances.sh start    - Start all 5 instances (host ports 7991-7995)"
echo -e "  ./run-instances.sh stop     - Stop all instances"
echo -e "  ./run-instances.sh restart  - Restart all instances (causes downtime)"
echo -e "  ./run-instances.sh update   - Rolling update (zero-downtime, recommended)"
echo -e "  ./run-instances.sh rollback - Rollback to previous version (zero-downtime)"
echo -e "  ./run-instances.sh cleanup  - Clean up untagged/dangling Docker images"
echo -e "  ./run-instances.sh status   - Show status of all instances"

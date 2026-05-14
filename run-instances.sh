#!/bin/bash

# Script to run multiple instances of ask-quran-adk
# Usage: ./run-instances.sh [start|stop|restart|update|rollback|cleanup|status]

set -e

IMAGE_NAME="ask-quran-adk:latest"
PREVIOUS_IMAGE="ask-quran-adk:previous"
CONTAINER_PREFIX="ask-quran-adk"
START_PORT=7991
NUM_INSTANCES=5
CONTAINER_PORT=7990   # Internal port the ADK API server listens on inside the container
READ_QURAN_API_URL=https://api.readquran.app
ENV_FILE="$HOME/ask-quran-adk/.env"
DOCKER_NETWORK="ask-quran-net"
SESSION_VOLUME="ask-quran-adk-sessions"   # Shared SQLite session store across all replicas

# Check if user needs sudo for docker
if docker ps >/dev/null 2>&1; then
    DOCKER_CMD="docker"
elif sudo docker ps >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
else
    echo "Error: Cannot access Docker. Please ensure Docker is installed and user has permissions."
    exit 1
fi

# Ensure docker network exists
ensure_network() {
    if ! $DOCKER_CMD network inspect "$DOCKER_NETWORK" >/dev/null 2>&1; then
        echo "Creating docker network '$DOCKER_NETWORK'..."
        $DOCKER_CMD network create "$DOCKER_NETWORK" >/dev/null
    fi
}

# Ensure shared session volume exists. All replicas mount this at /data so
# they share one SQLite file (sessions.db) — without this, nginx round-robin
# across instances would hit "Session not found" on every other request.
ensure_session_volume() {
    if ! $DOCKER_CMD volume inspect "$SESSION_VOLUME" >/dev/null 2>&1; then
        echo "Creating docker volume '$SESSION_VOLUME' for shared sessions..."
        $DOCKER_CMD volume create "$SESSION_VOLUME" >/dev/null
    fi
}

# Function to get container name for instance number
get_container_name() {
    local instance_num=$1
    echo "${CONTAINER_PREFIX}-${instance_num}"
}

# Function to get host port for instance number
get_port() {
    local instance_num=$1
    echo $((START_PORT + instance_num - 1))
}

# Function to check if image exists
image_exists() {
    $DOCKER_CMD images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | grep -q "^${IMAGE_NAME}$" || \
    $DOCKER_CMD images 2>/dev/null | grep -q "ask-quran-adk.*latest"
}

# Ensure .env exists, otherwise create a placeholder
ensure_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        echo "⚠️  .env file not found at $ENV_FILE — creating placeholder."
        echo "   You MUST set GOOGLE_API_KEY in this file before instances can serve requests."
        mkdir -p "$(dirname "$ENV_FILE")"
        cat > "$ENV_FILE" << EOF
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=
QURANAI_API_PORT=${CONTAINER_PORT}
READ_QURAN_API_URL=${READ_QURAN_API_URL}
EOF
    fi
}

# Function to start all instances
start_instances() {
    echo "Starting ${NUM_INSTANCES} instances of ask-quran-adk..."

    if ! image_exists; then
        echo "❌ Error: Image ${IMAGE_NAME} not found on server."
        echo ""
        echo "To deploy the image, run from your local machine:"
        echo "  ./deploy.sh"
        echo ""
        echo "Available images on server:"
        $DOCKER_CMD images 2>/dev/null | head -5
        exit 1
    fi

    ensure_network
    ensure_session_volume
    ensure_env_file

    for i in $(seq 1 $NUM_INSTANCES); do
        container_name=$(get_container_name $i)
        port=$(get_port $i)

        # Stop and remove existing container if it exists
        $DOCKER_CMD stop "$container_name" 2>/dev/null || true
        $DOCKER_CMD rm "$container_name" 2>/dev/null || true

        # Start new container
        echo "Starting instance $i on port $port..."
        $DOCKER_CMD run -d \
            --name "$container_name" \
            --restart unless-stopped \
            --network "$DOCKER_NETWORK" \
            -v "${SESSION_VOLUME}:/data" \
            -p "${port}:${CONTAINER_PORT}" \
            -e QURANAI_API_PORT=${CONTAINER_PORT} \
            --env-file "$ENV_FILE" \
            "$IMAGE_NAME"
    done

    echo "✅ All ${NUM_INSTANCES} instances started successfully!"
    echo ""
    echo "Instances running on ports:"
    for i in $(seq 1 $NUM_INSTANCES); do
        port=$(get_port $i)
        echo "  - Instance $i: http://localhost:$port"
    done
}

# Function to stop all instances
stop_instances() {
    echo "Stopping all instances..."

    for i in $(seq 1 $NUM_INSTANCES); do
        container_name=$(get_container_name $i)
        echo "Stopping instance $i ($container_name)..."
        $DOCKER_CMD stop "$container_name" 2>/dev/null || true
        $DOCKER_CMD rm "$container_name" 2>/dev/null || true
    done

    echo "✅ All instances stopped and removed."
}

# Function to restart all instances
restart_instances() {
    echo "Restarting all instances..."
    stop_instances
    sleep 2
    start_instances
}

# Function to check if instance is healthy
check_health() {
    local port=$1
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    return 1
}

# Function to perform rolling update (zero-downtime)
rolling_update() {
    echo "🔄 Starting rolling update (zero-downtime deployment)..."
    echo ""

    if ! image_exists; then
        echo "❌ Error: Image ${IMAGE_NAME} not found on server."
        echo ""
        echo "To deploy the image, run from your local machine:"
        echo "  ./deploy.sh"
        echo ""
        echo "Available images on server:"
        $DOCKER_CMD images 2>/dev/null | head -5
        exit 1
    fi

    ensure_network
    ensure_session_volume
    ensure_env_file

    for i in $(seq 1 $NUM_INSTANCES); do
        container_name=$(get_container_name $i)
        port=$(get_port $i)

        echo "📦 Updating instance $i/$NUM_INSTANCES (port $port)..."

        # Stop and remove old container
        if $DOCKER_CMD ps -a --format "{{.Names}}" | grep -q "^${container_name}$"; then
            echo "  Stopping old container..."
            $DOCKER_CMD stop "$container_name" >/dev/null 2>&1 || true
            $DOCKER_CMD rm "$container_name" >/dev/null 2>&1 || true
        fi

        # Start new container
        echo "  Starting new container..."
        $DOCKER_CMD run -d \
            --name "$container_name" \
            --restart unless-stopped \
            --network "$DOCKER_NETWORK" \
            -v "${SESSION_VOLUME}:/data" \
            -p "${port}:${CONTAINER_PORT}" \
            -e QURANAI_API_PORT=${CONTAINER_PORT} \
            --env-file "$ENV_FILE" \
            "$IMAGE_NAME" >/dev/null 2>&1

        # Wait for health check
        echo "  Waiting for health check..."
        if check_health "$port"; then
            echo "  ✅ Instance $i is healthy"
        else
            echo "  ⚠️  Warning: Instance $i health check failed, but continuing..."
        fi

        # Small delay before next instance
        if [ $i -lt $NUM_INSTANCES ]; then
            sleep 2
        fi
        echo ""
    done

    echo "✅ Rolling update complete! All ${NUM_INSTANCES} instances updated."
    echo ""
    echo "Instances running on ports:"
    for i in $(seq 1 $NUM_INSTANCES); do
        port=$(get_port $i)
        echo "  - Instance $i: http://localhost:$port"
    done

    # Clean up old/dangling images after update
    echo ""
    echo "🧹 Cleaning up old images..."
    $DOCKER_CMD image prune -f >/dev/null 2>&1 || true
    echo "✅ Cleanup complete"
}

# Function to rollback to previous version
rollback() {
    echo "🔄 Rolling back to previous version..."
    echo ""

    PREVIOUS_EXISTS=false
    if $DOCKER_CMD images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | grep -q "^${PREVIOUS_IMAGE}$" || \
       $DOCKER_CMD images 2>/dev/null | grep -q "ask-quran-adk.*previous"; then
        PREVIOUS_EXISTS=true
    fi

    if [ "$PREVIOUS_EXISTS" = "false" ]; then
        echo "❌ Error: No 'previous' version found. Cannot rollback."
        echo ""
        echo "Available images:"
        $DOCKER_CMD images 2>/dev/null | grep ask-quran-adk || echo "No ask-quran-adk images found"
        exit 1
    fi

    echo "Found previous version. Rolling back..."

    # Tag current 'latest' as 'old' (temporary)
    if image_exists; then
        CURRENT_IMAGE_ID=$($DOCKER_CMD images ${IMAGE_NAME} --format "{{.ID}}" 2>/dev/null | head -n 1)
        if [ ! -z "$CURRENT_IMAGE_ID" ]; then
            echo "Tagging current 'latest' as 'old'..."
            $DOCKER_CMD tag ${IMAGE_NAME} ask-quran-adk:old 2>/dev/null || true
        fi
    fi

    # Tag 'previous' as 'latest'
    echo "Tagging 'previous' as 'latest'..."
    $DOCKER_CMD tag ${PREVIOUS_IMAGE} ${IMAGE_NAME} 2>/dev/null || {
        echo "❌ Error: Failed to tag previous as latest"
        exit 1
    }

    # Tag 'old' (current latest) as 'previous' for future rollback
    if $DOCKER_CMD images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | grep -q "^ask-quran-adk:old$"; then
        echo "Tagging 'old' as 'previous'..."
        $DOCKER_CMD tag ask-quran-adk:old ${PREVIOUS_IMAGE} 2>/dev/null || true
        $DOCKER_CMD rmi ask-quran-adk:old 2>/dev/null || true
    fi

    echo "✅ Rollback complete! Now updating instances..."
    echo ""

    rolling_update
}

# Function to clean up old images
cleanup_images() {
    echo "🧹 Cleaning up old Docker images..."

    echo "Removing untagged/dangling images..."
    $DOCKER_CMD image prune -f

    echo ""
    echo "Current images:"
    $DOCKER_CMD images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" 2>/dev/null | grep -E "REPOSITORY|ask-quran-adk" || \
    $DOCKER_CMD images 2>/dev/null | grep ask-quran-adk || echo "No ask-quran-adk images found"
}

# Function to show status of all instances
show_status() {
    echo "Status of ask-quran-adk instances:"
    echo ""

    for i in $(seq 1 $NUM_INSTANCES); do
        container_name=$(get_container_name $i)
        port=$(get_port $i)

        if $DOCKER_CMD ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
            status=$($DOCKER_CMD ps --filter "name=${container_name}" --format "{{.Status}}")
            if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
                health="✅ Healthy"
            else
                health="⚠️  Unhealthy"
            fi
            echo "✅ Instance $i ($container_name):"
            echo "   Port: $port"
            echo "   Status: $status"
            echo "   Health: $health"
        elif $DOCKER_CMD ps -a --format "{{.Names}}" | grep -q "^${container_name}$"; then
            echo "⏸️  Instance $i ($container_name):"
            echo "   Port: $port"
            echo "   Status: Stopped"
        else
            echo "❌ Instance $i ($container_name):"
            echo "   Port: $port"
            echo "   Status: Not found"
        fi
        echo ""
    done
}

# Main script logic
case "${1:-start}" in
    start)
        start_instances
        ;;
    stop)
        stop_instances
        ;;
    restart)
        restart_instances
        ;;
    update|rolling-update)
        rolling_update
        ;;
    rollback)
        rollback
        ;;
    cleanup)
        cleanup_images
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 [start|stop|restart|update|rollback|cleanup|status]"
        echo ""
        echo "Commands:"
        echo "  start    - Start all ${NUM_INSTANCES} instances (default)"
        echo "  stop     - Stop all instances"
        echo "  restart  - Restart all instances (causes downtime)"
        echo "  update   - Rolling update (zero-downtime, updates one at a time)"
        echo "  rollback - Rollback to previous version (zero-downtime)"
        echo "  cleanup  - Clean up untagged/dangling Docker images"
        echo "  status   - Show status of all instances"
        exit 1
        ;;
esac

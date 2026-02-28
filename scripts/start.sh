#!/bin/bash
# Startup script: prune Docker garbage, then build and start
# Safely preserves mongo-data volume

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/log"
LOG_FILE="$LOG_DIR/consoleView.log"
ENV_FILE="$PROJECT_DIR/.env"

PRUNE=false
NGINX_ONLY=false
KILL_ALL=false

detect_container_identity() {
    if [[ "$OSTYPE" == "msys" ]] || grep -qi Microsoft /proc/version 2>/dev/null; then
        export CURRENT_UID=1000
        export CURRENT_GID=1000
    else
        export CURRENT_UID=$(id -u)
        export CURRENT_GID=$(id -g)
    fi
}

upsert_env_var() {
    local key="$1"
    local value="$2"
    if [ -f "$ENV_FILE" ] && grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s/^${key}=.*/${key}=${value}/" "$ENV_FILE"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

for arg in "$@"
do
    if [ "$arg" == "--prun" ]; then
        PRUNE=true
    fi
    if [ "$arg" == "--nginx" ]; then
        NGINX_ONLY=true
    fi
    if [ "$arg" == "--killall" ]; then
        KILL_ALL=true
    fi
    if [ "$arg" == "--help" ]; then
        echo -e "\nUsage: ./scripts/start.sh [OPTIONS]"
        echo "Options:"
        echo "  --prun   : Prune Docker garbage (stopped containers, images, volumes) before starting."
        echo "  --nginx  : Start only the Nginx service (rebuilds it)."
        echo "  --killall: Force stop and remove ALL Docker containers."
        echo "  --help   : Show this help message."
        exit 0
    fi
done

detect_container_identity
upsert_env_var "CURRENT_UID" "$CURRENT_UID"
upsert_env_var "CURRENT_GID" "$CURRENT_GID"

if [ "$KILL_ALL" = true ]; then
    echo -e "\n=== Killing ALL Docker containers ==="
    ids=$(docker container ps --all -q)
    if [ -n "$ids" ]; then
        docker container stop $ids 2>/dev/null
        docker container rm $ids 2>/dev/null
        echo "All containers stopped and removed."
    else
        echo "No containers found."
    fi
fi

if [ "$NGINX_ONLY" = true ]; then
    echo -e "\n=== Starting Nginx only ==="
    docker compose -p playground up -d --no-deps --build nginx
    exit 0
fi

if [ "$PRUNE" = true ]; then
    echo -e "\n=== Pruning Docker garbage ==="
    
    # Prune dangling images, stopped containers, build cache (never touches volumes)
    docker system prune -af 2>/dev/null
    
    # Prune only non-mongo volumes
    for vol in $(docker volume ls -q 2>/dev/null); do
        if [[ "$vol" != *mongo* ]]; then
            docker volume rm "$vol" 2>/dev/null && echo "  Removed volume: $vol"
        fi
    done
    
    echo "=== Prune complete ==="
else
    echo -e "\n=== Skipping prune (use --prun to enable) ==="
fi
echo -e "\n=== Starting app ==="

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Build and start — redirect all output to log file AND console
cd "$PROJECT_DIR"
docker compose -p playground up --build 2>&1 | tee "$LOG_FILE"

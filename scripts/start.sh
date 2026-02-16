#!/bin/bash
# Startup script: prune Docker garbage, then build and start
# Safely preserves mongo-data volume

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/log"
LOG_FILE="$LOG_DIR/consoleView.log"

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
echo -e "\n=== Starting app ==="

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Build and start — redirect all output to log file AND console
cd "$PROJECT_DIR"
docker compose up --build 2>&1 | tee "$LOG_FILE"

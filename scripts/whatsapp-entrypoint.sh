#!/bin/bash
set -e

# Default to 1500 if env vars are missing or empty
USER_ID=${CURRENT_UID:-1500}
GROUP_ID=${CURRENT_GID:-1500}

# Modify the internal appuser/media_group to match the host's UID/GID
groupmod -o -g "$GROUP_ID" media_group
usermod -o -u "$USER_ID" appuser

# Ensure the directory exists
mkdir -p /app/media_store/pending_media
# Set ownership to appuser
chown -R appuser:media_group /app/media_store/pending_media

# Step down from root and execute the CMD as appuser
exec gosu appuser "$@"

#!/bin/bash
# scripts/run-prod.sh - Start production server with static files

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Move to the project root (parent of scripts directory)
cd "$SCRIPT_DIR/.."

# Run uvicorn with production settings
# The --app-dir flag ensures proper module resolution
exec uv run uvicorn src.api_server:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 1
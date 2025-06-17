#!/bin/bash
# scripts/run-dev.sh - Start both backend and frontend development servers

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Move to the project root (parent of scripts directory)
cd "$SCRIPT_DIR/.."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting development servers...${NC}"

# Function to kill all child processes on exit
cleanup() {
    echo -e "\n${BLUE}Shutting down servers...${NC}"
    kill 0
}
trap cleanup EXIT

# Start backend
echo -e "${BLUE}Starting backend API...${NC}"
uv run uvicorn src.api_server:app --reload &

# Start frontend
echo -e "${BLUE}Starting frontend...${NC}"
cd ui && npm run dev &

# Wait for all background processes
wait
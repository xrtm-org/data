#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Setting up xrtm-data...${NC}"

if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Install: https://github.com/astral-sh/uv"
    exit 1
fi

echo -e "${GREEN}Syncing dependencies...${NC}"
uv sync

echo -e "${BLUE}Setup complete!${NC}"
echo -e "Run ${GREEN}uv run pytest${NC} to verify your environment."

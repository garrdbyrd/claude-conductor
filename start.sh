#!/bin/bash
# start.sh — Start the conductor (WebUI + MCP server).
# Safe to call from within a Claude Code conductor session.
# On first run, installs dependencies via uv sync.
set -e

CONDUCTOR_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$CONDUCTOR_DIR"

# First-time setup
uv sync --quiet

# Kill any stale instances
pkill -f "uv run webui/server.py" 2>/dev/null || true
pkill -f "uv run mcp_server.py"   2>/dev/null || true
sleep 0.3

nohup uv run webui/server.py > /tmp/conductor-webui.log 2>&1 &
nohup uv run mcp_server.py   > /tmp/conductor-mcp.log  2>&1 &

sleep 1

# Register MCP server globally so all Claude sessions have conductor tools
claude mcp add --transport sse --scope user conductor http://localhost:8766/sse 2>/dev/null || true

echo "Conductor started:"
echo "  WebUI      → http://localhost:9095"
echo "  MCP server → http://localhost:8766/sse"

#!/bin/bash

# run.sh — AI Social Media Manager Dev Runner
# Starts the FastAPI backend with hot-reload so any file change
# is automatically picked up without restarting the server manually.

set -e  # Exit immediately if any command fails

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"
VENV_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║      AI Social Media Manager — Dev Server       ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Verify the virtual environment exists ──────────────────────────────────
if [ ! -f "$VENV_UVICORN" ]; then
  echo "❌  Virtual environment not found at $BACKEND_DIR/.venv"
  echo "    Run this first to set it up:"
  echo "    cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "✅  Virtual environment found"
echo "📦  Python : $("$VENV_PYTHON" --version)"
echo "🌐  Backend : http://localhost:8001"
echo "📖  API Docs: http://localhost:8001/docs"
echo "🔄  Hot-reload is ON — save any file to apply changes instantly"
echo ""

# ── Free port 8001 if already in use ──────────────────────────────────────
# WHY? Prevents "Address already in use" error when re-running the script
# without manually killing the previous server process.
EXISTING_PID=$(lsof -ti tcp:8001 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
  echo "⚠️   Port 8001 is in use (PID $EXISTING_PID) — killing old process..."
  kill -9 $EXISTING_PID 2>/dev/null && sleep 1
  echo "✅  Port 8001 is now free"
  echo ""
fi
echo "──────────────────────────────────────────────────"
echo ""

# ── Start FastAPI with hot-reload ──────────────────────────────────────────
# --reload        : watches for file changes and restarts automatically
# --reload-dir    : only watch the app/ directory (avoids noise from .venv)
# --host 0.0.0.0  : accessible on local network (not just localhost)
# --port 8001     : our configured port
cd "$BACKEND_DIR"
"$VENV_UVICORN" app.main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --reload \
  --reload-dir app \
  --log-level info

#!/bin/bash

# run.sh — Start backend (FastAPI :8001) and frontend (Next.js :3000) together.
# Ctrl+C stops both.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_PYTHON="$BACKEND_DIR/.venv/bin/python"
VENV_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "Stopping servers..."
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  # Also clear anything still bound to our ports
  for port in 8001 3000; do
    pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
      kill $pids 2>/dev/null || true
    fi
  done
  echo "Done."
  exit 0
}

trap cleanup INT TERM

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   AI Social Media Manager — Dev (both apps)    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Checks ────────────────────────────────────────────────────────────────
if [ ! -f "$VENV_UVICORN" ]; then
  echo "Backend venv missing at $BACKEND_DIR/.venv"
  echo "Run:"
  echo "  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Frontend node_modules missing. Installing..."
  (cd "$FRONTEND_DIR" && npm install)
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js first."
  exit 1
fi

# ── Free ports if already in use ───────────────────────────────────────────
for port in 8001 3000; do
  EXISTING_PID=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [ -n "$EXISTING_PID" ]; then
    echo "Port $port in use (PID $EXISTING_PID) — freeing..."
    kill -9 $EXISTING_PID 2>/dev/null || true
    sleep 1
  fi
done

echo "Python  : $("$VENV_PYTHON" --version)"
echo "Backend : http://localhost:8001"
echo "API Docs: http://localhost:8001/docs"
echo "Frontend: http://localhost:3000"
echo "Hot-reload ON for both"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "──────────────────────────────────────────────────"
echo ""

# ── Backend ────────────────────────────────────────────────────────────────
cd "$BACKEND_DIR"
"$VENV_UVICORN" app.main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --reload \
  --reload-dir app \
  --log-level info &
BACKEND_PID=$!

# ── Frontend ───────────────────────────────────────────────────────────────
cd "$FRONTEND_DIR"
npm run dev -- --port 3000 &
FRONTEND_PID=$!

# Wait until either process exits (or Ctrl+C)
wait $BACKEND_PID $FRONTEND_PID
cleanup

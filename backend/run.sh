#!/usr/bin/env bash
# Mykare Voice Agent — backend launcher (Linux / macOS)
# Runs the LiveKit agent worker and the FastAPI server in parallel.
# Press Ctrl+C once to stop both cleanly.

set -e

cd "$(dirname "$0")"

# ── 1. Virtualenv ─────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "▶ Creating virtual environment…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# ── 2. Install deps if requirements changed ───────────────────────────────
if [ ! -f ".venv/.installed" ] || [ "requirements.txt" -nt ".venv/.installed" ]; then
  echo "▶ Installing Python dependencies…"
  pip install --upgrade pip > /dev/null
  pip install -r requirements.txt
  touch .venv/.installed
fi

# ── 3. Verify .env exists ─────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "❌ .env file is missing. Copy .env.example to .env and fill in your API keys first."
  exit 1
fi

# ── 4. One-time model download (silero VAD + turn detector) ───────────────
if [ ! -f ".venv/.models_downloaded" ]; then
  echo "▶ Downloading VAD + turn-detector models (one-time)…"
  python agent.py download-files || true
  touch .venv/.models_downloaded
fi

# ── 5. Launch BOTH processes in parallel ──────────────────────────────────
echo ""
echo "🚀 Starting LiveKit agent worker AND FastAPI HTTP server…"
echo "   • Agent worker: registering with LiveKit Cloud"
echo "   • HTTP API:     http://localhost:8000"
echo ""
echo "   (Press Ctrl+C once to stop both.)"
echo ""

# Trap Ctrl+C so we kill both children cleanly.
trap 'echo ""; echo "▶ Shutting down…"; kill 0; exit 0' INT TERM

python agent.py dev &
AGENT_PID=$!

uvicorn api:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Wait for either to exit; if one dies, kill the other.
wait -n $AGENT_PID $API_PID
echo "▶ One process exited — stopping the other…"
kill 0

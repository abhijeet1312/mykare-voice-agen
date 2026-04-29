#!/usr/bin/env bash
# Mykare Voice Agent — frontend launcher (Linux / macOS)

set -e
cd "$(dirname "$0")"

# ── 1. Install deps if needed ────────────────────────────────────────────
if [ ! -d "node_modules" ]; then
  echo "▶ Installing frontend dependencies (this takes ~1 min)…"
  npm install
fi

# ── 2. Make sure .env exists ─────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "▶ Creating .env from template…"
  cp .env.example .env
fi

# ── 3. Launch dev server ─────────────────────────────────────────────────
echo ""
echo "🚀 Starting Vite dev server at http://localhost:5173"
echo "   (Make sure the backend is also running.)"
echo ""

npm run dev

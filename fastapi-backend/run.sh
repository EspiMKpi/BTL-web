#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# run.sh — start the VozFlix FastAPI backend locally
# Usage:  ./run.sh          (default port 8000)
#         ./run.sh 9000      (custom port)
# ──────────────────────────────────────────────────────────────────────────
set -euo pipefail

PORT="${1:-8000}"

# Activate venv if present
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    # Windows (Git Bash / MSYS2)
    # shellcheck disable=SC1091
    source .venv/Scripts/activate
fi

# Load .env if python-dotenv isn't handling it
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

echo "Starting VozFlix API on http://localhost:${PORT}"
exec uvicorn app.main:app --reload --port "${PORT}" --host 0.0.0.0

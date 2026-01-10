#!/bin/bash
# RAGex Start (root-level) — standard uvicorn

set -e
cd "$(dirname "$0")/.."  # repo root

if [ -f backend/.venv/bin/activate ]; then
  source backend/.venv/bin/activate
fi

export TOKENIZERS_PARALLELISM=false
export PYTHONWARNINGS="ignore::UserWarning"

echo "🚀 Starting Backend at http://127.0.0.1:8000"
cd backend
# Disabled reload for better stability in 'production' feel
uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info
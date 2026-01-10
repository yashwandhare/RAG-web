#!/bin/bash
# RAGex: Interactive CLI launcher
# Ensures venv + dependencies, sets env, then hands off to rag_cli.py

set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# 1) Ensure Python
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 not found. Install Python 3.8+ and retry."; exit 1;
fi

# 2) Ensure venv + deps
if [ ! -d "$ROOT_DIR/backend/.venv" ]; then
  echo "Creating virtual environment at backend/.venv"
  python3 -m venv "$ROOT_DIR/backend/.venv"
  source "$ROOT_DIR/backend/.venv/bin/activate"
  pip install --upgrade pip
  pip install -r "$ROOT_DIR/backend/requirements.txt"
  # Try to install Playwright browsers (optional)
  playwright install chromium || true
else
  source "$ROOT_DIR/backend/.venv/bin/activate"
fi

# 3) Env selection: prefer backend/.env, else root .env
if [ -f "$ROOT_DIR/backend/.env" ]; then
  export DOTENV_PATH="$ROOT_DIR/backend/.env"
elif [ -f "$ROOT_DIR/.env" ]; then
  export DOTENV_PATH="$ROOT_DIR/.env"
fi

# 4) Clean logs
export TOKENIZERS_PARALLELISM=false
export PYTHONWARNINGS="ignore::UserWarning"

# 5) Run interactive CLI (it will start server if needed)
python "$ROOT_DIR/scripts/rag_cli.py"

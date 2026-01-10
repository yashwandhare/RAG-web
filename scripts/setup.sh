#!/bin/bash
# RAGex Setup (root-level)
# Creates venv, installs deps, installs Playwright + OS deps, prepares .env, and preps extension

set -e
cd "$(dirname "$0")/.."  # go to repo root

echo "== RAGex Setup =="

# 1. Python check
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 not found. Install Python 3.10+ and retry."; exit 1;
fi

# 2. venv
if [ ! -d backend/.venv ]; then
  echo "Creating venv at backend/.venv";
  python3 -m venv backend/.venv;
fi
source backend/.venv/bin/activate

# 3. deps
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# 4. playwright browsers (with OS dependencies)
echo "Installing Playwright browsers..."
playwright install chromium --with-deps

# 5. Extension Setup (Crucial for V3)
echo "Setting up Browser Extension..."
if [ ! -f extension/marked.min.js ]; then
    echo "Downloading marked.min.js for extension..."
    # Download marked.js (lightweight markdown parser)
    curl -L -o extension/marked.min.js https://cdn.jsdelivr.net/npm/marked/marked.min.js
fi

# 6. env
if [ ! -f backend/.env ] && [ -f backend/.env.example ]; then
  cp backend/.env.example backend/.env
  echo "⚠️  Created backend/.env. PLEASE EDIT IT and add your GROQ_API_KEY."
fi

# 7. Create Data Directory
mkdir -p backend/data/chroma_db

echo "✅ Setup complete. Run 'scripts/rag.sh' to start."
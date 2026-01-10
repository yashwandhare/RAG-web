```text
██████╗  █████╗  ██████╗ ███████╗██╗  ██╗
██╔══██╗██╔══██╗██╔════╝ ██╔════╝╚██╗██╔╝
██████╔╝███████║██║  ███╗█████╗   ╚███╔╝ 
██╔══██╗██╔══██║██║   ██║██╔══╝   ██╔██╗ 
██║  ██║██║  ██║╚██████╔╝███████╗██╔╝ ██╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝

```

# RAGex Companion

**Your intelligent browsing companion.**
RAGex is a privacy-focused RAG (Retrieval-Augmented Generation) system that runs locally. It crawls websites, indexes them into a local vector database, and lets you ask questions or generate summaries using Groq's Llama 3.1.

---

## ✨ Features

* **Deep Research:** Crawls and indexes websites into a local knowledge base.
* **Privacy First:** Vector database runs locally (ChromaDB); no data sent to 3rd parties except the LLM.
* **Smart Search:** Uses adaptive retrieval with confidence scores.
* **Browser Integration:** Includes a glassmorphic Chrome Extension for side-panel research.
* **Fast:** Powered by FastAPI and Groq hardware acceleration.

## 🚀 Quick Start

### 1. Prerequisites

* **Python 3.10+** (Python 3.14 is **not** supported yet)
* **Groq API Key** (Get a free key at [console.groq.com](https://console.groq.com))

### 2. Installation

Run the automated setup script. This creates a virtual environment, installs dependencies, and downloads the necessary browser engines.

**Linux / macOS:**

```bash
./scripts/setup.sh

```

**Windows:**

```cmd
scripts\setup.bat

```

> **Note:** The setup script will create a `.env` file in the `backend/` folder. You **must** open this file and paste your `GROQ_API_KEY`.

### 3. Start the Backend

Start the high-performance API server.

**Linux / macOS:**

```bash
./scripts/start.sh

```

**Windows:**

```cmd
scripts\start.bat

```

*The server will start at `http://127.0.0.1:8000`.*

### 4. Install the Extension

1. Open Chrome/Edge and go to `chrome://extensions`.
2. Enable **Developer Mode** (top right toggle).
3. Click **Load Unpacked**.
4. Select the `extension/` folder from this project.
5. Open the side panel and click **Connect**.

---

## 🛠️ CLI Mode (Optional)

Don't want to use the extension? You can use the terminal interface.

```bash
# Ensure backend is running, then:
./scripts/rag.sh

```

## 🏗️ Tech Stack

* **Backend:** FastAPI, Uvicorn, Python 3.10+
* **AI/ML:** Llama 3.1 (via Groq), ChromaDB, SentenceTransformers
* **Crawling:** Playwright (Headless Chromium)
* **Frontend:** Vanilla JS, Glassmorphism CSS

## ⚠️ Limitations

* **Media:** Does not yet support Images/OCR or PDF files.
* **Auth:** Cannot index pages behind a login wall (Netflix, Facebook, etc).
* **Javascript:** Heavy SPA pages might index partially; static pages work best.

---

*License: MIT*

- **Python 3.8+** (tested on Python 3.10+)
- **pip** package manager
- **Git** (to clone the repository)
- **Groq API Key** (free at https://console.groq.com/keys)

### Backend Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd RAGex/backend
```

2. **Create and activate virtual environment:**
```bash
# On Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# On Windows
python -m venv .venv
.venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** The installation includes:
- PyTorch CPU-only version (no CUDA/GPU required)
- Playwright for web crawling (Chromium browser will be downloaded automatically)
- ChromaDB for vector storage
- Sentence Transformers for embeddings

4. **Install Playwright browsers:**
```bash
playwright install chromium
```

5. **Configure environment variables:**
```bash
cp .env.example .env
```

Edit `.env` and add your **Groq API key**:
```env
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=llama-3.1-8b-instant
CHROMA_PERSIST_DIR=./data/chroma_db
```
Env lookup order at runtime: `backend/.env` → repo root `.env` → system environment.

6. **Start the API server:**
```bash
# Recommended: Use the start script (simple, minimal)
scripts/start.sh  # Linux/macOS
# OR
python scripts/rag_cli.py  # Interactive start + CLI

# Alternative: Direct uvicorn (from backend folder)
cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend runs at: `http://127.0.0.1:8000`  
API docs at: `http://127.0.0.1:8000/docs`

✅ **Server is ready when you see:**
```
🚀 RAG Backend Starting...
✅ Groq API Key loaded: gsk_...
✅ RAG Backend ready to serve requests
```

### Browser Extension Setup

1. **Open Chrome/Edge extensions page:**
   - Chrome: Navigate to `chrome://extensions/`
   - Edge: Navigate to `edge://extensions/`

2. **Enable Developer Mode:**
   - Toggle the "Developer mode" switch in the top-right corner

3. **Load the extension:**
   - Click "Load unpacked"
   - Select the `extension/` folder from this project

4. **Pin the extension:**
   - Click the puzzle icon in the browser toolbar
   - Find "RAGex Companion" and pin it

5. **Usage:**
   - Navigate to any webpage
   - Click the RAGex icon to open the side panel
   - Click "Connect" to index and analyze the page
   - Start asking questions!

### Frontend Setup (Optional Web UI)

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Serve with any static server:
```bash
python -m http.server 8080
```

Frontend runs at: `http://localhost:8080`

## API Endpoints

- `GET /` - Health check
- `POST /api/v1/index` - Index a URL for RAG
  - Request: `{"url": "https://example.com"}`
  - Returns indexed content with metadata
- `POST /api/v1/query` - Query indexed content
  - Request: `{"question": "Your question here"}`
  - Returns answer with sources, confidence score, and follow-up questions
  - "summarize this page" triggers summary mode

### CLI Test (no extension)

Run the server, then from `backend`:
```bash
scripts/rag.sh        # starts venv + interactive CLI
# or
python scripts/rag_cli.py  # if venv already active
```
The script will:
- Ask for a URL to index
- Wait until indexing finishes (minimal logs)
- Ask a question (default: "What is this page about?")
- Return answer, confidence, and sources

## Usage

1) Index a page
- Provide a URL in the UI and click Connect. The backend fetches HTML, chunks it, embeds, and stores in ChromaDB.

2) Ask questions or summaries
- Ask specific questions for targeted retrieval, or type "summarize this page" for broader coverage.

3) Review answers
- Responses include cited sources, a confidence score, and suggested follow-ups.

## Roadmap

- JS rendering for SPA-heavy pages (Playwright)
- PDF/DOCX/PPTX ingestion
- Image/OCR support
- YouTube transcript ingestion

## Troubleshooting

### Extension shows "Connection Failed"
1. Verify backend is running at `http://127.0.0.1:8000`
2. Check browser console for CORS errors
3. Ensure `.env` has valid `GROQ_API_KEY`
4. Try restarting the backend server

### "Index not found" errors
- Normal during initial indexing (wait 10-30 seconds)
- Data persists in `backend/data/chroma_db/`
- Delete this folder to reset the database

### Playwright/Chromium issues
```bash
# Reinstall Playwright browsers
playwright install chromium
```

### ChromaDB telemetry warnings
- These are harmless warnings and can be ignored
- Data is stored persistently in `./data/chroma_db`

### PyTorch installation issues
- The project uses CPU-only PyTorch (no CUDA required)
- If installation fails, try:
  ```bash
  pip install torch==2.9.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu
  ```

### Virtual environment not activating
```bash
# Linux/macOS
deactivate  # if already in a venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

# Windows
deactivate
rmdir /s .venv
python -m venv .venv
.venv\Scripts\activate
```

## Development

The backend and frontend are completely decoupled and communicate only via REST API. You can:
- Run them on different ports/servers
- Deploy them separately
- Replace the frontend with any other client (mobile app, CLI, etc.)

### Project Structure
```
backend/
├── .venv/              # Virtual environment (created during setup)
├── data/
│   └── chroma_db/      # Persistent vector database
├── app/
│   ├── api/            # FastAPI routes
│   ├── core/           # Config & logging
│   └── rag/            # RAG implementation
├── requirements.txt    # Python dependencies
└── .env                # Environment variables (create from .env.example)

extension/
├── manifest.json       # Chrome extension config
├── sidepanel.html      # Extension UI
├── sidepanel.js        # Extension logic
└── background.js       # Service worker
```

## License

MIT License - see [LICENSE](LICENSE) file for details

## RAGex Companion
RAGex runs locally on your machine. It crawls websites, saves them into a private database, and lets you chat with them using AI. It works as a Chrome Extension or a standalone CLI tool.

---

## Tech Stack

* **Core:** Python 3.10+, FastAPI, Uvicorn
* **AI Engine:** Groq (Llama 3.1), SentenceTransformers (Embeddings), PyTorch (CPU)
* **Database:** ChromaDB (Local Vector Store)
* **Scraper:** Playwright (Headless Chromium), BeautifulSoup4
* **Frontend:** Chrome Extension (Manifest V3), Vanilla JS

---

## Quick Start

### 1. Prerequisites

* **Python 3.10+**
* **Groq API Key** (Free at [console.groq.com](https://console.groq.com))

### 2. One-Time Setup

Run the setup script to create the environment and download necessary packages.

**Linux / macOS:**

```bash
./scripts/setup.sh

```

**Windows:**

```cmd
scripts\setup.bat

```

> **Important:** The script creates a `.env` file in `backend/`. Open it and paste your `GROQ_API_KEY`.

---

## How to Run

### Browser Extension

This starts the backend API so the extension can connect.

1. **Start the Server:**
* Linux/Mac: `./scripts/start.sh`
* Windows: `scripts\start.bat`


2. **Install in Chrome/Edge:**
* Go to `chrome://extensions`
* Enable **Developer Mode** (top right)
* Click **Load Unpacked**
* Select the `extension/` folder


3. **Use:** Open the side panel on any website and click **Connect**.

### Option B: CLI Mode

You can use RAGex entirely from the terminal. This script automatically starts the backend if it's not running.

```bash
./scripts/rag.sh

```

---

## Limitations

* **Media:** Does not support Images, PDFs, or YouTube yet.
* **Auth:** Cannot access pages behind a login (e.g., Netflix, Gmail).
* **Dynamic Sites:** Works best on static text pages; heavy JavaScript apps may be incomplete.

---

*License: MIT*

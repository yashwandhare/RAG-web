# RAG Web

A production-ready Retrieval-Augmented Generation (RAG) system with a FastAPI backend and web frontend for intelligent question-answering over web content.

## Features

- 🕷️ Web content crawling and indexing
- 🔍 Vector-based semantic search using ChromaDB
- 🤖 LLM-powered response generation (Google Gemini)
- 🚀 RESTful API architecture
- 💻 Terminal-style web interface

## Project Structure

```
RAG-web/
├── backend/              # FastAPI backend service
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Configuration & logging
│   │   ├── rag/         # RAG system (crawler, chunker, retriever, etc.)
│   │   └── main.py      # FastAPI application
│   ├── data/            # Database storage
│   │   └── chroma_db/   # Vector database
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # Static web interface
│   └── index.html       # Single-page app
├── README.md
└── LICENSE
```

## Tech Stack

**Backend:**
- FastAPI - Modern Python web framework
- ChromaDB - Vector database for embeddings
- Google Gemini - Large language model
- BeautifulSoup4 - Web scraping
- Sentence Transformers - Text embeddings

**Frontend:**
- Vanilla HTML/CSS/JS - No dependencies, lightweight

## Quick Start

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Add your GOOGLE_API_KEY to .env
```

4. Start the API server:
```bash
uvicorn app.main:app --reload
```

Backend runs at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

### Frontend Setup

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
- `POST /api/v1/query` - Query indexed content

## Development

The backend and frontend are completely decoupled and communicate only via REST API. You can:
- Run them on different ports/servers
- Deploy them separately
- Replace the frontend with any other client (mobile app, CLI, etc.)

## License

MIT License - see [LICENSE](LICENSE) file for details

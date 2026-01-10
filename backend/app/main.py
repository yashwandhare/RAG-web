"""
RAG Backend - Main Application Entry Point
===========================================
"""
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
from pathlib import Path

# 1. Load Env
load_dotenv()

# 2. Fix Tokenizer Warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.index import router
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 RAG Backend Starting...")
    
    api_key = settings.GROQ_API_KEY
    if api_key:
        logger.info(f"✅ Groq API Key loaded: {api_key[:5]}...")
    else:
        logger.error("❌ GROQ_API_KEY not found in environment!")
    
    logger.info("✅ RAG Backend ready to serve requests")
    yield
    # Shutdown
    logger.info("🛑 RAG Backend shutting down gracefully...")

app = FastAPI(
    title="RAG Backend",
    description="Production-grade Retrieval-Augmented Generation system",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# STRICT Production CORS
app.add_middleware(
    CORSMiddleware,
    # In production, replace "*" with specific extension ID or frontend URL
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

app.include_router(router, prefix="/api/v1", tags=["RAG"])

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "RAG Backend", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    # Production: Disable reload, use 0.0.0.0
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
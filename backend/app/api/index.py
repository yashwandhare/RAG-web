from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.rag.crawler import crawl_site_async
from app.rag.chunker import chunk_pages_smart
from app.rag.store import VectorStore
from app.rag.generator import generate_answer, contextualize_question, analyze_content
from app.rag.retriever import AdaptiveRetriever
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

store = VectorStore()
retriever = AdaptiveRetriever(store)

class IndexRequest(BaseModel):
    url: str
    max_pages: int = Field(default=10, ge=1, le=settings.MAX_PAGES_PER_INDEX)
    max_depth: int = Field(default=2, ge=1, le=settings.MAX_CRAWL_DEPTH)

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    history: List[Message] = Field(default_factory=list)
    include_sources: bool = True
    debug: bool = False

# New Model for Analytics
class AnalysisResponse(BaseModel):
    topics: List[str]
    type: str
    summary: str

async def process_indexing(url: str, max_pages: int, max_depth: int):
    try:
        logger.info(f"🚀 Starting background crawl: {url}")
        pages = await crawl_site_async(url, max_pages, max_depth)
        
        if not pages:
            logger.error(f"❌ Indexing ABORTED: No content found at {url}.")
            store.clear()
            store.add([{
                "id": "error_msg", 
                "text": f"System Alert: The website {url} could not be indexed. It might be blocking bots or have no text content.", 
                "source": "system"
            }])
            return

        chunks = chunk_pages_smart(pages)
        if not chunks:
            logger.error("❌ Indexing Failed: Content found but chunking produced 0 results.")
            return

        store.clear()
        store.add(chunks)
        logger.info(f"✅ Indexing complete. Added {len(chunks)} chunks.")
        
    except Exception as e:
        logger.error(f"❌ Indexing failed exception: {e}")

@router.post("/index")
async def index_endpoint(req: IndexRequest, tasks: BackgroundTasks):
    tasks.add_task(process_indexing, req.url, req.max_pages, req.max_depth)
    return {"status": "accepted", "message": "Indexing started."}

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint():
    """Smart Analytics: Inspects the vector store content."""
    # Retrieve random chunks to analyze
    # We query with a generic term to get a spread of content
    results = store.query("summary overview introduction", n_results=5)
    
    contexts = []
    if results['documents'] and results['documents'][0]:
        contexts = results['documents'][0]
    
    if not contexts:
        return {"topics": [], "type": "Empty", "summary": "No content indexed."}
        
    analysis = analyze_content(contexts)
    return analysis

@router.post("/query")
async def query_endpoint(req: QueryRequest):
    start_time = datetime.now()
    
    is_summary = "summarize" in req.question.lower() or "summary" in req.question.lower()
    
    if is_summary:
        search_query = req.question
    else:
        q_dict = [m.dict() for m in req.history]
        search_query = contextualize_question(req.question, q_dict)
    
    retrieval = await retriever.retrieve(search_query, summary_mode=is_summary)
    
    if not retrieval["relevant"]:
        return {
            "answer": "I cannot find relevant information in the indexed content.",
            "refusal": True,
            "sources": [],
            "confidence": 0.0,
            "confidence_score": 0.0,
            "suggested_questions": []
        }
    
    gen_result = generate_answer(req.question, retrieval["contexts"], summary_mode=is_summary)
    duration = (datetime.now() - start_time).total_seconds()
    
    return {
        "answer": gen_result["answer"],
        "refusal": gen_result["refusal"],
        "confidence": "high" if retrieval["confidence"] > 0.7 else "medium",
        "confidence_score": retrieval["confidence"],
        "sources": retrieval["sources"] if req.include_sources else [],
        "suggested_questions": gen_result.get("suggestions", []),
        "response_time": round(duration, 2)
    }
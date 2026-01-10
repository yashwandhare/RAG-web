import asyncio
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logger import setup_logger
from app.rag.chunker import chunk_pages_smart
from app.rag.crawler import crawl_site_async
from app.rag.generator import analyze_content, contextualize_question, generate_answer
from app.rag.retriever import AdaptiveRetriever
from app.rag.store import VectorStore

logger = setup_logger(__name__)
router = APIRouter()

# Global instances (Thread-safe enough for this scale)
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
    url: str | None = None

class AnalysisResponse(BaseModel):
    topics: List[str]
    type: str
    summary: str

class AnalyzeRequest(BaseModel):
    url: str

async def process_indexing(url: str, max_pages: int, max_depth: int) -> None:
    """
    Runs the full indexing pipeline.
    CRITICAL FIX: CPU-bound tasks are offloaded to threads to prevent blocking the API.
    """
    try:
        logger.info(f"🚀 Starting background crawl: {url}")
        
        # 1. Clear DB (Blocking I/O -> Thread)
        await asyncio.to_thread(store.clear)
        
        # 2. Crawl (Async I/O -> Native Await)
        pages = await crawl_site_async(url, max_pages, max_depth)
        
        if not pages:
            logger.error(f"❌ Indexing ABORTED: No content found at {url}.")
            await asyncio.to_thread(store.clear)
            await asyncio.to_thread(store.add, [{
                "id": "error_msg", 
                "text": f"System Alert: The website {url} could not be indexed.", 
                "source": "system"
            }])
            return

        # 3. Chunking (CPU Bound -> Thread)
        chunks = await asyncio.to_thread(chunk_pages_smart, pages)
        
        if not chunks:
            logger.error("❌ Indexing Failed: Content found but chunking produced 0 results.")
            return

        # 4. Store (Blocking I/O -> Thread)
        # Note: We clear again just to be safe before the final add
        await asyncio.to_thread(store.clear)
        await asyncio.to_thread(store.add, chunks)
        
        logger.info(f"✅ Indexing complete. Added {len(chunks)} chunks.")
        
    except Exception as e:
        logger.error(f"❌ Indexing failed exception: {e}")

@router.post("/index")
async def index_endpoint(req: IndexRequest, tasks: BackgroundTasks) -> dict:
    # Pass arguments to the background task wrapper
    tasks.add_task(process_indexing, req.url, req.max_pages, req.max_depth)
    return {"status": "accepted", "message": "Indexing started."}

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(req: AnalyzeRequest) -> AnalysisResponse:
    # Query is blocking, wrap it
    results = await asyncio.to_thread(store.query, "summary overview introduction", n_results=20)

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []

    filtered_contexts: List[str] = []
    if documents and metadatas and documents[0] and metadatas[0]:
        for doc, meta in zip(documents[0], metadatas[0]):
            source = (meta or {}).get("source")
            if source == req.url:
                filtered_contexts.append(doc)

    if not filtered_contexts:
        return AnalysisResponse(
            topics=[],
            type="Empty",
            summary="Indexing in progress or no content for this URL yet.",
        )

    # LLM analysis is blocking (network), wrap it
    analysis = await asyncio.to_thread(analyze_content, filtered_contexts)
    
    return AnalysisResponse(
        topics=analysis.get("topics", []),
        type=analysis.get("type", "Web Content"),
        summary=analysis.get("summary", "Content indexed successfully."),
    )

@router.post("/query")
async def query_endpoint(req: QueryRequest) -> dict:
    start_time = datetime.now()
    
    is_summary = "summarize" in req.question.lower() or "summary" in req.question.lower()
    
    # Contextualization (LLM Call -> Blocking)
    if is_summary:
        search_query = req.question
    else:
        q_dict = [m.dict() for m in req.history]
        search_query = await asyncio.to_thread(contextualize_question, req.question, q_dict)
    
    # Retrieval (DB Call -> Async Wrapper inside retriever)
    retrieval = await retriever.retrieve(search_query, summary_mode=is_summary)
    
    if not retrieval["relevant"]:
        return {
            "answer": "I cannot find relevant information in the indexed content.",
            "refusal": True,
            "sources": [],
            "confidence": "low",
            "confidence_score": 0.0,
            "suggested_questions": []
        }
    
    contexts = retrieval["contexts"]
    context_sources = retrieval.get("context_sources") or []
    source_objects = retrieval.get("sources") or []

    if is_summary and req.url:
        filtered = [
            (text, src_obj)
            for text, src in zip(contexts, context_sources)
            for src_obj in source_objects
            if src == req.url
        ]
        if filtered:
            contexts, _ = zip(*filtered)
            contexts = list(contexts)

    # Generation (LLM Call -> Blocking)
    gen_result = await asyncio.to_thread(generate_answer, req.question, contexts, summary_mode=is_summary)
    
    duration = (datetime.now() - start_time).total_seconds()
    
    # Suggestion fallback logic
    suggestions = gen_result.get("suggestions", []) or []
    if len(suggestions) < 2:
        base = req.question.rstrip(" ?.")
        fallback = [
            f"What else should I know about {base}?",
            f"Can you highlight any limitations about {base}?",
            f"Are there related topics on {base}?",
        ]
        for s in fallback:
            if len(suggestions) >= 3: break
            if s not in suggestions: suggestions.append(s)

    return {
        "answer": gen_result["answer"],
        "refusal": gen_result["refusal"],
        "confidence": "high" if retrieval["confidence"] > 0.7 else "medium",
        "confidence_score": retrieval["confidence"],
        "sources": source_objects,
        "suggested_questions": suggestions,
        "response_time": round(duration, 2)
    }
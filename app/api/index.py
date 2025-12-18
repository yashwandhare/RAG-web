from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List
from app.rag.crawler import crawl_site_async
from app.rag.chunker import chunk_pages_smart
from app.rag.store import VectorStore
from app.rag.retriever import AdaptiveRetriever
from app.rag.generator import generate_answer, contextualize_question
from app.core.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)
store = VectorStore()
retriever = AdaptiveRetriever(store)

class IndexReq(BaseModel):
    url: str
    max_pages: int = 10

class QueryReq(BaseModel):
    question: str
    history: List[dict] = []
    include_sources: bool = True
    debug: bool = False

async def process_indexing(url: str, max_pages: int):
    try:
        logger.info(f"🚀 Starting background crawl: {url}")
        pages = await crawl_site_async(url, max_pages)
        if pages:
            chunks = chunk_pages_smart(pages)
            store.clear()
            store.add(chunks)
            logger.info("✅ Indexing complete.")
        else:
            logger.warning("❌ No pages found.")
    except Exception as e:
        logger.error(f"Indexing Error: {e}")

@router.post("/index")
async def index_endpoint(req: IndexReq, tasks: BackgroundTasks):
    tasks.add_task(process_indexing, req.url, req.max_pages)
    return {"status": "accepted", "message": f"Indexing {req.url} in background."}

@router.post("/query")
async def query_endpoint(req: QueryReq):
    # 1. Contextualize (SYNC call)
    q = contextualize_question(req.question, req.history)
    
    # 2. Retrieve (ASYNC call)
    retrieval = await retriever.retrieve(q)
    
    if not retrieval["relevant"]:
        return {
            "answer": "I cannot find relevant information on the website.",
            "refusal": True,
            "sources": [],
            "confidence": 0.0
        }
    
    # 3. Generate (SYNC call)
    gen = generate_answer(req.question, retrieval["contexts"])
    
    return {
        "answer": gen["answer"],
        "refusal": gen["refusal"],
        "sources": retrieval["sources"],
        "confidence": retrieval["confidence"]
    }
import asyncio
from typing import Any, Dict, List

from app.core.config import settings
from app.core.logger import setup_logger
from app.rag.generator import generate_hyde_doc

logger = setup_logger(__name__)

class AdaptiveRetriever:
    """Hybrid retriever that augments vector search with HyDE when needed."""

    def __init__(self, store: Any) -> None:
        self.store = store

    def _extract_snippet(self, text: str, max_words: int = 15) -> str:
        """Extract first N words from text as snippet for deep linking."""
        words = text.split()[:max_words]
        return " ".join(words)

    async def retrieve(self, query: str, summary_mode: bool = False) -> Dict[str, Any]:
        # 1. Standard Vector Search (Run in Thread)
        threshold = settings.DISTANCE_THRESHOLD
        if len(query.split()) < 4: threshold -= 0.05
        
        k_results = settings.TOP_K_RESULTS + 5 if summary_mode else settings.TOP_K_RESULTS
        
        # FIX: ChromaDB client is blocking, so we await it in a thread
        results = await asyncio.to_thread(self.store.query, query, n_results=k_results)
        
        # Helper to process results
        def process_results(raw_res):
            if not raw_res or not raw_res.get("documents") or not raw_res["documents"][0]:
                return []
            docs = raw_res["documents"][0]
            dists = raw_res["distances"][0]
            metas = raw_res["metadatas"][0]
            
            valid_items = []
            for doc, dist, meta in zip(docs, dists, metas):
                # In summary mode, accept almost anything. In query mode, enforce threshold.
                if summary_mode or dist < threshold:
                    valid_items.append(
                        {
                            "text": doc,
                            "source": meta.get("source"),
                            "snippet": self._extract_snippet(doc),
                            "dist": dist,
                        }
                    )
            return valid_items

        valid = process_results(results)
        
        # 2. HyDE Boost (Smart Automation)
        # If we found nothing or confidence is low, generate a hallucination and search with THAT.
        best_confidence = 1 - valid[0]["dist"] if valid else 0
        
        if not summary_mode and (not valid or best_confidence < 0.35):
            logger.info(f"🧠 Engaging HyDE for difficult query: '{query}'")
            
            # FIX: LLM generation is blocking (network I/O), run in thread
            hypothetical_answer = await asyncio.to_thread(generate_hyde_doc, query)
            logger.debug(f"   HyDE Document: {hypothetical_answer[:50]}...")
            
            # Search again with the hypothetical answer (Blocking DB call)
            hyde_results = await asyncio.to_thread(self.store.query, hypothetical_answer, n_results=k_results)
            hyde_valid = process_results(hyde_results)
            
            # Merge unique results
            existing_texts = {v["text"] for v in valid}
            for item in hyde_valid:
                if item["text"] not in existing_texts:
                    valid.append(item)
            
            # Re-sort by distance
            valid.sort(key=lambda x: x["dist"])

        if not valid:
            return {
                "relevant": False,
                "contexts": [],
                "context_sources": [],
                "sources": [],
                "confidence": 0,
            }

        # Build source objects with URL and snippet for deep linking
        source_objects = []
        seen_urls = set()
        for v in valid:
            url = v["source"]
            if url and url not in seen_urls:
                source_objects.append({
                    "url": url,
                    "snippet": v["snippet"]
                })
                seen_urls.add(url)

        return {
            "relevant": True,
            "contexts": [v["text"] for v in valid],
            "context_sources": [v["source"] for v in valid],
            "sources": source_objects,
            "confidence": 1 - valid[0]["dist"],
        }
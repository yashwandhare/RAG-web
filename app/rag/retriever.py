from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

class AdaptiveRetriever:
    def __init__(self, store):
        self.store = store

    async def retrieve(self, query: str):
        # 1. Adaptive Thresholding
        threshold = settings.DISTANCE_THRESHOLD
        
        # Stricter for short queries ("Who is he?")
        if len(query.split()) < 4: 
            threshold -= 0.05 
            
        # Lenient for long queries ("Detail the specific differences between X and Y")
        if len(query.split()) > 10: 
            threshold += 0.05
        
        # 2. Query DB
        results = self.store.query(query, n_results=settings.TOP_K_RESULTS)
        
        if not results['documents'] or not results['documents'][0]:
            return {"relevant": False, "contexts": [], "confidence": 0}

        docs = results['documents'][0]
        dists = results['distances'][0]
        metas = results['metadatas'][0]
        
        # 3. Filter by Threshold
        valid = []
        for doc, dist, meta in zip(docs, dists, metas):
            if dist < threshold:
                valid.append({"text": doc, "source": meta["source"], "dist": dist})
        
        # 4. Fallback/Refusal
        if not valid:
            logger.warning(f"❌ Refused. Top dist: {dists[0]:.3f} > Threshold: {threshold:.3f}")
            return {
                "relevant": False, 
                "contexts": [], 
                "confidence": 0, 
                "debug_dist": dists[0]
            }

        return {
            "relevant": True,
            "contexts": [v["text"] for v in valid],
            "sources": list(set(v["source"] for v in valid)),
            "confidence": 1 - valid[0]["dist"]
        }
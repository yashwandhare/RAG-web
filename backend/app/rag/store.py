import chromadb
from chromadb.utils import embedding_functions
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

# Initialize embedding function once
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=settings.EMBEDDING_MODEL
)

class VectorStore:
    def __init__(self):
        # PRODUCTION FIX: Use PersistentClient (ChromaDB 0.4+)
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        
        self.collection = self.client.get_or_create_collection(
            name="website_rag",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"📂 DB Loaded: {self.collection.count()} chunks")

    def clear(self):
        self.client.delete_collection("website_rag")
        self.collection = self.client.create_collection(
            name="website_rag", embedding_function=ef
        )

    def add(self, chunks: list):
        if not chunks: return
        batch_size = 100
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            docs = [c["text"] for c in batch]
            ids = [c["id"] for c in batch]
            # ChromaDB expects metadata values to be str, int, float, or bool
            metadatas = [
                {k: v for k, v in c.items() if k not in ("id", "text") and v is not None}
                for c in batch
            ]
            
            try:
                self.collection.add(
                    ids=ids,
                    documents=docs,
                    metadatas=metadatas
                )
            except Exception as e:
                logger.error(f"Add error: {e}")
                
        logger.info(f"✅ Added {len(chunks)} chunks")

    def query(self, text: str, n_results: int = None) -> dict:
        """Standard public API wrapper for retrieval"""
        n = n_results or settings.TOP_K_RESULTS
        try:
            return self.collection.query(
                query_texts=[text],
                n_results=n,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"Query error: {e}")
            return {"documents": [], "metadatas": [], "distances": []}
import chromadb
from chromadb.utils import embedding_functions
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

# Initialize embedding function
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=settings.EMBEDDING_MODEL
)

class VectorStore:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            self.collection = self.client.get_or_create_collection(
                name="website_rag",
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"📂 ChromaDB loaded with {self.collection.count()} chunks")
        except Exception as e:
            logger.error(f"❌ ChromaDB Init Failed: {e}")
            raise

    def clear(self):
        self.client.delete_collection("website_rag")
        self.collection = self.client.create_collection(
            name="website_rag", embedding_function=ef
        )
        logger.info("🗑️ Index cleared")

    def add(self, chunks: list):
        if not chunks: return
        
        # Batch processing
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            self.collection.add(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
                metadatas=[{"source": c["source"]} for c in batch]
            )
        logger.info(f"💾 Stored {len(chunks)} chunks")

    def query(self, text: str, n_results: int = 5):
        return self.collection.query(query_texts=[text], n_results=n_results)
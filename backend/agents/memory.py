import os
import logging
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# ── Data security: strictly local storage ──
DB_DIR = Path(os.getenv("CHROMA_DB_DIR", "data/chroma_db"))
DB_DIR.mkdir(parents=True, exist_ok=True)

try:
    os.chmod(DB_DIR, 0o700) # Only owner can read/write
except Exception:
    pass

# Initialize ChromaDB persistent client
client = chromadb.PersistentClient(path=str(DB_DIR))

# Use default local ONNX embedding. Keeps your data completely off-cloud.
ef = embedding_functions.DefaultEmbeddingFunction()

docs_collection = client.get_or_create_collection(
    name="documents",
    embedding_function=ef
)

def chunk_text(text: str, chunk_size=1200, overlap=200) -> list[str]:
    """Splits a large document into smaller chunks for Vector DB ingestion."""
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + chunk_size])
        i += chunk_size - overlap
    return chunks

def ingest_document(doc_id: str, text: str, source: str):
    """Chunks internal data and saves securely in the local Vector DB."""
    logger.info(f"Ingesting document {doc_id} into memory (source: {source})")
    chunks = chunk_text(text)
    
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": source, "doc_id": doc_id} for _ in range(len(chunks))]
    
    try:
        # Check if exists and remove old chunks to prevent duplicates
        existing = docs_collection.get(where={"doc_id": doc_id})
        if existing and existing["ids"]:
            docs_collection.delete(ids=existing["ids"])
            
        docs_collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        return True
    except Exception as e:
        logger.error(f"Ingestion error for {doc_id}: {e}")
        return False

def search_memory(query: str, n_results: int = 4) -> str:
    """Searches the local knowledge base efficiently."""
    try:
        results = docs_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if not results["documents"] or not results["documents"][0]:
            return "No relevant information found in memory."
            
        blocks = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            blocks.append(f"--- Document Source: {meta.get('source', 'Unknown')} ---\n{doc}")
            
        return "\n\n".join(blocks)
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        return f"Error accessing memory: {e}"

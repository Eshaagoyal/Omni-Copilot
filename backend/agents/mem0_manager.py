import os
import logging
from mem0 import Memory

logger = logging.getLogger(__name__)

config = {
    "llm": {
        "provider": "groq",
        "config": {
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "temperature": 0.0,
            "api_key": os.getenv("GROQ_API_KEY"),
        }
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2"
        }
    },
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "mem0_user_memory",
            "path": os.getenv("CHROMA_DB_DIR", "data/chroma_db")
        }
    }
}

memory = None
try:
    memory = Memory.from_config(config)
except Exception as e:
    logger.error(f"Failed to initialize Mem0: {e}")

def save_user_fact(user_id: str, fact: str) -> str:
    """Save an important fact about the user."""
    if not memory: return "Error: Mem0 uninitialized."
    try:
        memory.add(fact, user_id=user_id)
        return "Fact remembered."
    except Exception as e:
        return f"Error saving memory: {e}"

def search_user_facts(user_id: str, query: str) -> str:
    """Retrieve facts about the user related to a query."""
    if not memory: return "Error: Mem0 uninitialized."
    try:
        res = memory.search(query, user_id=user_id)
        if not res: return "No relevant memories found."
        
        # Format might vary by mem0 version, typically res is a list of dicts
        facts = []
        for r in res:
            if isinstance(r, dict) and "memory" in r:
                facts.append("- " + str(r["memory"]))
            elif hasattr(r, 'memory'):
                facts.append("- " + str(r.memory))
            else:
                facts.append("- " + str(r))
        return "\n".join(facts)
    except Exception as e:
        return f"Error searching memory: {e}"

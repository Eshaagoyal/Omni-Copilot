import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("VECTORLESS_DB_DIR", "data/vectorless_db/omni.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

try:
    os.chmod(DB_PATH.parent, 0o700)
except Exception:
    pass

def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_conn()
    c = conn.cursor()
    # Create an FTS5 virtual table for lightning fast keyword matching (Vectorless)
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS documents 
        USING fts5(doc_id, title, source, content)
    ''')
    conn.commit()
    conn.close()

init_db()

def ingest_text_vectorless(doc_id: str, content: str, source: str, title: str = ""):
    """Ingest files/emails strictly using Vectorless Full-Text Search."""
    conn = _get_conn()
    c = conn.cursor()
    try:
        # Avoid duplicate documents
        c.execute('DELETE FROM documents WHERE doc_id = ?', (doc_id,))
        c.execute('''
            INSERT INTO documents (doc_id, title, source, content)
            VALUES (?, ?, ?, ?)
        ''', (doc_id, title, source, content))
        conn.commit()
        logger.info(f"Vectorless ingest success: {doc_id} ({source})")
        return True
    except Exception as e:
        logger.error(f"Vectorless ingest error for {doc_id}: {e}")
        return False
    finally:
        conn.close()

def search_exact_text(query: str, limit: int = 5) -> str:
    """Uses BM25 keyword matching to find specific filesystem/mail contents instantly."""
    conn = _get_conn()
    c = conn.cursor()
    try:
        # We also grab snippets to save AI context window
        # SQLite FTS5 snippet function arguments: table, column_idx, start_match, end_match, ellipsis, max_tokens
        # 'content' is column index 3
        safe_query = query.replace('"', '').replace("'", "").replace('*', '')
        # FTS5 uses specific syntax. Wrapping in quotes forces phrase matching securely.
        fmt_query = f'"{safe_query}"'
        c.execute('''
            SELECT source, title, snippet(documents, 3, '[MATCH]', '[/MATCH]', '...', 64) as match_snippet
            FROM documents
            WHERE documents MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (fmt_query, limit))
        
        rows = c.fetchall()
        if not rows:
            return "No exact matches found in vectorless database."
            
        blocks = []
        for row in rows:
            blocks.append(f"Source: {row['source']}\nTitle: {row['title']}\nSnippet:\n{row['match_snippet']}")
            
        return "\n\n---\n\n".join(blocks)
    except Exception as e:
        logger.error(f"Vectorless search error: {e}")
        return f"Error running exact search: {e}"
    finally:
        conn.close()

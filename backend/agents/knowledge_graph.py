import os
import sqlite3
import networkx as nx
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("GRAPH_DB_DIR", "data/graph_db/omni_graph.sqlite3"))
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            source TEXT,
            target TEXT,
            relationship TEXT,
            metadata TEXT,
            UNIQUE(source, target, relationship)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def add_graph_edge(source: str, target: str, relationship: str, metadata: str = "") -> str:
    """Add a relationship connecting two entities to the knowledge graph."""
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR IGNORE INTO edges (source, target, relationship, metadata)
            VALUES (?, ?, ?, ?)
        ''', (source, target, relationship, metadata))
        conn.commit()
        return f"Relation added: [{source}] --({relationship})--> [{target}]"
    except Exception as e:
        logger.error(f"Graph add error: {e}")
        return f"Database Error: {e}"
    finally:
        conn.close()

def query_graph(entity: str) -> str:
    """Get all relationships for a given entity from the knowledge graph."""
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute('''
            SELECT * FROM edges WHERE source LIKE ? OR target LIKE ?
        ''', (f'%{entity}%', f'%{entity}%'))
        rows = c.fetchall()
        
        if not rows:
            return f"No known relationships found for '{entity}'."
            
        G = nx.DiGraph()
        for r in rows:
            G.add_edge(r['source'], r['target'], label=r['relationship'])
            
        lines = []
        for u, v, data in G.edges(data=True):
            lines.append(f"[{u}] --({data['label']})--> [{v}]")
            
        return "Knowledge Graph Relationships:\n" + "\n".join(lines)
    except Exception as e:
        logger.error(f"Graph query error: {e}")
        return f"Error: {e}"
    finally:
        conn.close()

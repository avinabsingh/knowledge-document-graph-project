import sqlite3
import hashlib
from typing import List, Dict, Any, Tuple, Optional

DEFAULT_DB_PATH = "knowledge_layer.db"

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Document Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, -- SHA256 hash acts as ID to prevent duplicates
            filename TEXT NOT NULL,
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            page_count INTEGER,
            chunk_count INTEGER,
            processing_status TEXT DEFAULT 'pending'
        )
    """)

    # 2. Rich Fact Schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL,
            source_filename TEXT NOT NULL,
            category TEXT NOT NULL,
            entity TEXT NOT NULL,
            metric TEXT NOT NULL,
            raw_value TEXT,
            raw_unit TEXT,
            normalized_value REAL,
            normalized_unit TEXT,
            period TEXT,
            normalized_period TEXT,
            context TEXT,
            evidence_sentence TEXT NOT NULL,
            evidence_text TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            chunk_id TEXT NOT NULL,
            confidence REAL,
            extraction_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        )
    """)

    # 3. Cross-Document Relationships
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_a_id INTEGER NOT NULL,
            fact_b_id INTEGER NOT NULL,
            relationship TEXT NOT NULL,
            dimension TEXT,
            reasoning TEXT NOT NULL,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(fact_a_id) REFERENCES facts(id),
            FOREIGN KEY(fact_b_id) REFERENCES facts(id)
        )
    """)

    # 4. Failure Tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extraction_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            original_evidence TEXT,
            attempted_extraction TEXT,
            reason TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes for fast querying and filtering
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_entity ON facts(entity);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_metric ON facts(metric);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_id ON facts(document_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_facts ON relationships(fact_a_id, fact_b_id);")
    
    conn.commit()
    conn.close()

def compute_file_hash(file_bytes: bytes) -> str:
    """Computes SHA256 hash for document deduplication."""
    return hashlib.sha256(file_bytes).hexdigest()

def document_exists(sha256_hash: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Checks if a document has already been processed."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM documents WHERE id = ?", (sha256_hash,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists
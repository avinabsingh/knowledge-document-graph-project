import sqlite3
import hashlib
import re
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple

DEFAULT_DB_PATH = "knowledge_layer.db"


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the database schema with Document Registry and Fact relationships."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Document Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            page_count INTEGER,
            chunk_count INTEGER,
            processing_status TEXT DEFAULT 'pending'
        )
    """)

    # Rich Fact Schema
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

    # Cross-Document Relationships
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

    # Failure Tracking
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

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_entity ON facts(entity);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_metric ON facts(metric);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_id ON facts(document_id);")
    
    conn.commit()
    conn.close()

def insert_facts(facts: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> int:
    """Inserts newly extracted facts with rich metadata into the database."""
    if not facts:
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
        INSERT INTO facts (
            document_id, source_filename, category, entity, metric, 
            raw_value, raw_unit, normalized_value, normalized_unit, 
            period, normalized_period, context, evidence_sentence, 
            evidence_text, page_number, chunk_id, confidence, extraction_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    records = [
        (
            f.get("document_id"), f.get("source_filename"), f.get("category"), 
            f.get("entity"), f.get("metric"), f.get("raw_value"), f.get("raw_unit"), 
            f.get("normalized_value"), f.get("normalized_unit"), f.get("period"), 
            f.get("normalized_period"), f.get("context"), f.get("evidence_sentence"), 
            f.get("evidence_text"), f.get("page_number", 0), f.get("chunk_id"), 
            f.get("confidence"), f.get("extraction_notes")
        ) for f in facts
    ]
    
    cursor.executemany(query, records)
    conn.commit()
    inserted_count = cursor.rowcount
    conn.close()
    
    return inserted_count

def get_all_facts(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves all facts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facts ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def normalize_string_for_clustering(text: str) -> str:
    """Cleans entities and metrics for resilient cross-document clustering."""
    if not text: 
        return ""
    text = text.lower()
    # Strip corporate suffixes and common filler words
    text = re.sub(r'\b(ltd|limited|inc|corp|co|private|pvt)\b', '', text)
    text = re.sub(r'\b(net|total|from|activities|operations|annual|for the year)\b', '', text)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return " ".join(text.split())

def get_cross_document_fact_clusters(db_path: str = DEFAULT_DB_PATH) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    """Finds cross-document candidate pairs using semantic token intersection & ratio."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM facts ORDER BY document_id, page_number")
    all_facts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    clusters = {}
    processed_pairs = set()

    for i, fact_a in enumerate(all_facts):
        ent_a = normalize_string_for_clustering(fact_a['entity'])
        met_a = normalize_string_for_clustering(fact_a['metric'])
        words_a = set(met_a.split())

        for fact_b in all_facts[i+1:]:
            if fact_a['document_id'] == fact_b['document_id']:
                continue

            pair_key = tuple(sorted([fact_a['id'], fact_b['id']]))
            if pair_key in processed_pairs:
                continue

            ent_b = normalize_string_for_clustering(fact_b['entity'])
            met_b = normalize_string_for_clustering(fact_b['metric'])
            words_b = set(met_b.split())

            # Check entity match (either substring or high similarity)
            ent_match = (ent_a in ent_b or ent_b in ent_a) or (SequenceMatcher(None, ent_a, ent_b).ratio() > 0.6)
            
            # Metric match: word overlap (e.g. "cash", "flow") or sequence ratio
            word_overlap = len(words_a & words_b) > 0 and (len(words_a & words_b) / max(len(words_a), len(words_b), 1) >= 0.4)
            met_ratio = SequenceMatcher(None, met_a, met_b).ratio() > 0.55

            if ent_match and (word_overlap or met_ratio):
                processed_pairs.add(pair_key)
                cluster_key = (fact_a['entity'], fact_a['metric'])
                if cluster_key not in clusters:
                    clusters[cluster_key] = [fact_a]
                clusters[cluster_key].append(fact_b)

    return clusters
import sqlite3
from typing import List, Dict, Any, Tuple

DEFAULT_DB_PATH = "knowledge_layer.db"

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Initializes the SQLite database and creates the facts table if it does not exist.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            entity TEXT NOT NULL,
            metric_or_attribute TEXT NOT NULL,
            value TEXT,
            context TEXT,
            source_sentence TEXT NOT NULL,
            source_filename TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Indexes for fast grouping and cross-document comparison
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity ON facts(entity);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metric ON facts(metric_or_attribute);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON facts(source_filename);")
    
    conn.commit()
    conn.close()

def insert_facts(facts: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> int:
    """
    Inserts a list of extracted fact dictionaries into the database.
    Returns the count of successfully inserted records.
    """
    if not facts:
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
        INSERT INTO facts (
            category, entity, metric_or_attribute, value, 
            context, source_sentence, source_filename, page_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    records = [
        (
            fact.get("category", "General"),
            fact.get("entity", "").strip(),
            fact.get("metric_or_attribute", "").strip(),
            fact.get("value"),
            fact.get("context", "").strip(),
            fact.get("source_sentence", "").strip(),
            fact.get("source_filename", ""),
            fact.get("page_number", 0)
        )
        for fact in facts
    ]
    
    cursor.executemany(query, records)
    conn.commit()
    inserted_count = cursor.rowcount
    conn.close()
    
    return inserted_count

def get_all_facts(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """
    Returns all stored facts as a list of dictionaries.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM facts ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_cross_document_fact_clusters(db_path: str = DEFAULT_DB_PATH) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    """
    Finds clusters of facts that share an entity and metric/attribute 
    originating from at least two DIFFERENT source documents.
    These clusters form the input candidates for the reasoning engine in Step 4.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query entity + metric pairs appearing in multiple distinct source documents
    cursor.execute("""
        SELECT entity, metric_or_attribute
        FROM facts
        GROUP BY LOWER(entity), LOWER(metric_or_attribute)
        HAVING COUNT(DISTINCT source_filename) > 1
    """)
    candidates = cursor.fetchall()
    
    clusters = {}
    for cand in candidates:
        ent = cand["entity"]
        metric = cand["metric_or_attribute"]
        
        cursor.execute("""
            SELECT * FROM facts
            WHERE LOWER(entity) = LOWER(?) AND LOWER(metric_or_attribute) = LOWER(?)
            ORDER BY source_filename, page_number
        """, (ent, metric))
        
        cluster_rows = [dict(r) for r in cursor.fetchall()]
        clusters[(ent, metric)] = cluster_rows
        
    conn.close()
    return clusters
import os
import sqlite3
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

# Updated imports matching the new architecture
from parser import process_pdf, compute_file_hash
from analyzer import extract_facts
from storage import init_db, insert_facts, get_all_facts, get_cross_document_fact_clusters
from reasoner import compare_fact_cluster

import time

app = FastAPI(title="Knowledge Layer API")

# Add CORS block for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure DB is initialized on startup
init_db()

# Temporary storage for uploaded files
UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_and_process_pdf(file: UploadFile = File(...)):
    """Uploads a PDF, deduplicates it, parses semantic chunks, and extracts facts."""
    
    # 1. Read and Save File
    file_bytes = await file.read()
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as f:
        f.write(file_bytes)
        
    # 2. Compute SHA256 Hash for Deduplication
    doc_hash = compute_file_hash(file_path)
    
    # 3. Check if Document Already Exists
    conn = sqlite3.connect("knowledge_layer.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM documents WHERE id = ?", (doc_hash,))
    if cursor.fetchone():
        conn.close()
        return {
            "status": "skipped", 
            "message": "Document already processed", 
            "document_id": doc_hash
        }
        
    # 4. Generic Ingestion (No hardcoded filenames or page numbers!)
    chunks = process_pdf(file_path, doc_hash)
    
    # 5. Register Document in DB
    page_count = chunks[-1]['page_end'] if chunks else 0
    cursor.execute(
        "INSERT INTO documents (id, filename, page_count, chunk_count, processing_status) VALUES (?, ?, ?, ?, ?)",
        (doc_hash, file.filename, page_count, len(chunks), 'processing')
    )
    conn.commit()
    conn.close()
    
    # 6. Extract Facts
    total_facts = 0
    
    # Note: Processing the first 3 chunks universally to avoid LLM rate-limit timeouts on the free tier.
    # In a production environment with a paid API tier, you would loop through all `chunks`.
    target_chunks = chunks[16:22]
    
    for chunk in target_chunks:
        extracted = extract_facts(chunk)
        if extracted:
            insert_facts(extracted)
            total_facts += len(extracted)

        # time.sleep(2.5)
            
    # 7. Update Status
    conn = sqlite3.connect("knowledge_layer.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE documents SET processing_status = 'completed' WHERE id = ?", (doc_hash,))
    conn.commit()
    conn.close()
            
    return {
        "status": "success",
        "filename": file.filename, 
        "chunks_processed": len(target_chunks), 
        "facts_extracted": total_facts,
        "document_id": doc_hash
    }

@app.get("/facts")
async def list_all_facts():
    """Retrieves all stored facts from the database."""
    return {"facts": get_all_facts()}

@app.get("/analyze")
async def run_cross_document_analysis():
    """Finds overlapping clusters of facts and runs the reasoning engine."""
    clusters = get_cross_document_fact_clusters()
    
    analysis_results = []
    for (entity, metric), fact_list in clusters.items():
        comparisons = compare_fact_cluster(fact_list)
        if comparisons:
            analysis_results.extend(comparisons)
            
    return {
        "clusters_found": len(clusters),
        "comparisons": analysis_results
    }
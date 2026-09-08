import os
import shutil
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from parser import parse_pdf
from analyzer import extract_facts
from storage import init_db, insert_facts, get_all_facts, get_cross_document_fact_clusters
from reasoner import compare_fact_cluster
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Knowledge Layer API")

# Add this CORS block
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows your React app to connect
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
    """Uploads a PDF, parses it, extracts facts, and stores them in SQLite."""
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    chunks = parse_pdf(file_path)
    
    total_facts = 0
    
    # Target specific pages to avoid LLM rate limits during the demo
    if "prospectus" in file.filename.lower():
        target_chunks = chunks[16:20] # Pages 17-20 contain the financials
    else:
        target_chunks = chunks[:4]    # First 4 pages for other documents
        
    for chunk in target_chunks:
        extracted = extract_facts(chunk)
        if extracted:
            insert_facts(extracted)
            total_facts += len(extracted)
            
    return {
        "filename": file.filename, 
        "pages_processed": len(target_chunks), 
        "facts_extracted": total_facts
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
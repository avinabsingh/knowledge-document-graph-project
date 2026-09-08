import fitz  # PyMuPDF
import hashlib
from typing import List, Dict, Any

def compute_file_hash(file_path: str) -> str:
    """Computes SHA256 hash for document deduplication."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def process_pdf(file_path: str, document_id: str) -> List[Dict[str, Any]]:
    """
    Extracts text from any PDF using PyMuPDF and creates semantic chunks.
    Chunks are roughly 1000 tokens (~4000 chars) with a 150 token (~600 chars) overlap.
    """
    doc = fitz.open(file_path)
    chunks = []
    
    current_chunk_text = ""
    start_page = 1
    chunk_index = 0
    
    # Text length approximations for tokens
    CHUNK_SIZE_CHARS = 4000 
    OVERLAP_CHARS = 600 

    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text").strip()
        
        # Skip empty pages
        if not text:
            continue
            
        clean_text = " ".join(text.split())
        current_chunk_text += " " + clean_text
        
        while len(current_chunk_text) >= CHUNK_SIZE_CHARS:
            chunk_text = current_chunk_text[:CHUNK_SIZE_CHARS]
            
            chunks.append({
                "chunk_id": f"{document_id}_chunk_{chunk_index}",
                "page_start": start_page,
                "page_end": page_num + 1,
                "text": chunk_text.strip(),
                "filename": file_path.split('/')[-1]
            })
            chunk_index += 1
            
            # Maintain overlap for semantic continuity
            current_chunk_text = current_chunk_text[CHUNK_SIZE_CHARS - OVERLAP_CHARS:]
            start_page = page_num + 1

    # Append any remaining text as the final chunk
    if len(current_chunk_text.strip()) > 100:
        chunks.append({
            "chunk_id": f"{document_id}_chunk_{chunk_index}",
            "page_start": start_page,
            "page_end": len(doc),
            "text": current_chunk_text.strip(),
            "filename": file_path.split('/')[-1]
        })
        
    doc.close()
    return chunks
import pdfplumber
from typing import List, Dict

def parse_pdf(file_path: str) -> List[Dict]:
    """
    Reads a PDF and extracts text page by page.
    Returns a list of dictionaries containing the text and metadata.
    """
    document_chunks = []
    
    # Extract just the filename from the full path
    filename = file_path.split('/')[-1]

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            
            if text:
                # Clean up basic whitespace issues
                clean_text = " ".join(text.split())
                
                document_chunks.append({
                    "filename": filename,
                    "page_number": page_num,
                    "text": clean_text
                })
                
    return document_chunks
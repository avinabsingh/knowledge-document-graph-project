import os
from parser import parse_pdf

if __name__ == "__main__":
    # Pointing directly to the Delhivery prospectus excerpt from the starter dataset
    # We use double backslashes or raw strings for Windows paths if needed, 
    # but forward slashes work fine in Python on Windows too.
    test_pdf_path = "starter-datasets/delhivery/01-delhivery-prospectus-2022-excerpt.pdf"
    
    # Safety check to ensure the folder is in the right place
    if not os.path.exists(test_pdf_path):
        print(f"Error: Could not find {test_pdf_path}.")
        print("Please ensure the 'starter-datasets' folder is unzipped in the project root.")
        exit(1)

    print(f"Loading and parsing {test_pdf_path}...\n")
    chunks = parse_pdf(test_pdf_path)
    
    print(f"Successfully extracted {len(chunks)} pages of text.\n")
    print("-" * 50)
    
    # Print the first two pages to verify metadata and text extraction
    for chunk in chunks[:2]:
        print(f"Source Document : {chunk['filename']}")
        print(f"Page Number     : {chunk['page_number']}")
        print(f"Text Preview    : {chunk['text'][:250]}...\n")
        print("-" * 50)
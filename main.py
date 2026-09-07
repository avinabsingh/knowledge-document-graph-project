import os
import json
from dotenv import load_dotenv
from parser import parse_pdf
from analyzer import extract_facts

load_dotenv()

if __name__ == "__main__":
    test_pdf_path = "starter-datasets/delhivery/01-delhivery-prospectus-2022-excerpt.pdf"

    if not os.path.exists(test_pdf_path):
        print(f"Error: {test_pdf_path} not found.")
        exit(1)

    print("Step 1: Reading PDF chunks...")
    chunks = parse_pdf(test_pdf_path)

    # Page 18 (index 17) has key operational and financial metrics in the prospectus
    sample_chunk = chunks[17]
    print(f"Step 2: Sending Page {sample_chunk['page_number']} to Groq ({sample_chunk['filename']})...\n")

    facts = extract_facts(sample_chunk)

    print(f"Extraction complete! Found {len(facts)} grounded facts:\n")
    print(json.dumps(facts, indent=2))
import os
import json
from dotenv import load_dotenv
from parser import parse_pdf
from analyzer import extract_facts
from storage import init_db, insert_facts, get_all_facts

load_dotenv()

if __name__ == "__main__":
    test_pdf_path = "starter-datasets/delhivery/01-delhivery-prospectus-2022-excerpt.pdf"

    if not os.path.exists(test_pdf_path):
        print(f"Error: {test_pdf_path} not found.")
        exit(1)

    print("Step 3.1: Initializing knowledge database...")
    init_db()

    print("Step 3.2: Reading PDF chunks...")
    chunks = parse_pdf(test_pdf_path)

    # Use Page 18 where we know facts exist
    sample_chunk = chunks[17]
    print(f"Step 3.3: Extracting facts from Page {sample_chunk['page_number']}...")
    facts = extract_facts(sample_chunk)
    print(f"Extracted {len(facts)} facts from LLM.")

    print("Step 3.4: Storing facts into SQLite...")
    inserted_count = insert_facts(facts)
    print(f"Stored {inserted_count} records into knowledge_layer.db.\n")

    print("-" * 50)
    print("Step 3.5: Reading all facts back from database to verify persistence:")
    persisted_facts = get_all_facts()
    for row in persisted_facts[:3]:
        print(f"ID #{row['id']} | [{row['category']}] {row['entity']} -> {row['metric_or_attribute']}")
        print(f"  Value    : {row['value']}")
        print(f"  Context  : {row['context']}")
        print(f"  Evidence : \"{row['source_sentence']}\"")
        print(f"  Source   : {row['source_filename']} (Page {row['page_number']})\n")
    print(f"... Total records in storage: {len(persisted_facts)}")
    print("-" * 50)
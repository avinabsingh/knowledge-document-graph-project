import os
import json
from dotenv import load_dotenv
from parser import parse_pdf
from analyzer import extract_facts
from storage import init_db, insert_facts, get_all_facts, get_cross_document_fact_clusters
from reasoner import compare_fact_cluster

load_dotenv()

PDF_PATHS = [
    "starter-datasets/delhivery/01-delhivery-prospectus-2022-excerpt.pdf",
    "starter-datasets/delhivery/02-delhivery-annual-report-fy24-excerpt.pdf"
]

if __name__ == "__main__":
    print("Step 4.1: Initializing Database...")
    init_db()

    # To ensure representative clusters without burning rate limits,
    # we process selected high-density metric pages from both documents.
    targets = [
        {"path": PDF_PATHS[0], "pages": [17, 18]}, # Prospectus key financial summaries
        {"path": PDF_PATHS[1], "pages": [1, 2]}     # FY24 Report financial highlights
    ]

    for target in targets:
        if not os.path.exists(target["path"]):
            print(f"Skipping {target['path']} (file not found)")
            continue

        print(f"\nProcessing {os.path.basename(target['path'])}...")
        chunks = parse_pdf(target["path"])
        
        for p_idx in target["pages"]:
            if p_idx < len(chunks):
                chunk = chunks[p_idx]
                print(f"  -> Extracting from Page {chunk['page_number']}...")
                extracted = extract_facts(chunk)
                insert_facts(extracted)
                print(f"     Stored {len(extracted)} facts.")

    print("\n" + "=" * 60)
    print("Step 4.2: Querying Multi-Document Candidate Clusters...")
    clusters = get_cross_document_fact_clusters()
    print(f"Found {len(clusters)} shared (Entity, Metric) clusters spanning multiple files.")
    
    if not clusters:
        print("Note: No cross-document overlap found in these small test pages yet.")
        print("Simulating a cluster comparison to verify the reasoning engine:")
        sample_facts = get_all_facts()[:2]
        if len(sample_facts) >= 2:
            results = compare_fact_cluster(sample_facts)
            print(json.dumps(results, indent=2))
    else:
        print("\nStep 4.3: Running LLM Cross-Document Reasoning Engine...")
        for (ent, metric), fact_list in clusters.items():
            print(f"\nComparing Cluster: Entity='{ent}', Metric='{metric}' ({len(fact_list)} facts):")
            results = compare_fact_cluster(fact_list)
            for res in results:
                print(f"\n  [Verdict]: {res['relationship']}")
                if res['reconciliation_dimension']:
                    print(f"  [Dimension]: {res['reconciliation_dimension']}")
                print(f"  [Reasoning]: {res['explanation']}")
                print(f"  [Fact A ID]: {res['fact_a_id']} vs [Fact B ID]: {res['fact_b_id']}")

    print("\n" + "=" * 60)
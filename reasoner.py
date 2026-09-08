import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL_NAME = "openai/gpt-oss-120b"

class FactComparisonResult(BaseModel):
    relationship: str = Field(description="Strictly: 'CORROBORATION', 'CONTRADICTION', 'RECONCILED_BY_CONTEXT', or 'UNRELATED'")
    reasoning: str = Field(description="Detailed logical reasoning explaining the classification.")
    dimension: Optional[str] = Field(description="Reconciliation dimension if applicable.")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    fact_a_id: int = Field(description="Database ID of the first fact")
    fact_b_id: int = Field(description="Database ID of the second fact")

class CrossDocumentAnalysis(BaseModel):
    comparisons: List[FactComparisonResult]

def compare_fact_cluster(cluster: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyzes a cluster of facts and persists the relationship results."""
    if len(cluster) < 2:
        return []

    system_prompt = (
        "You are an expert investigative auditor comparing facts extracted from multiple filings. "
        "Classify how these facts relate across documents into one of these categories:\n"
        "1. 'CORROBORATION': The facts reinforce or confirm each other.\n"
        "2. 'CONTRADICTION': Genuine direct factual clash.\n"
        "3. 'RECONCILED_BY_CONTEXT': Apparent contradiction resolved by temporal differences, scope, or units.\n"
        "4. 'UNRELATED': The facts discuss different metrics and cannot be compared.\n\n"
        "Leverage normalized_value and normalized_period to detect true matches.\n"
        "You MUST reply with a JSON object containing a 'comparisons' array adhering to this schema:\n"
        "{\n"
        '  "comparisons": [\n'
        "    {\n"
        '      "relationship": "CORROBORATION" | "CONTRADICTION" | "RECONCILED_BY_CONTEXT" | "UNRELATED",\n'
        '      "reasoning": "Detailed logical reasoning",\n'
        '      "dimension": "time" | "scope" | "units" | "accounting_method" | "geography" | "entity_change" | null,\n'
        '      "confidence": float,\n'
        '      "fact_a_id": int,\n'
        '      "fact_b_id": int\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    facts_summary = []
    for f in cluster:
        facts_summary.append(
            f"Fact ID: {f['id']}\n"
            f"Document: {f['source_filename']} (Chunk {f['chunk_id']})\n"
            f"Entity: {f['entity']} | Metric: {f['metric']}\n"
            f"Raw Value: {f['raw_value']} | Normalized: {f['normalized_value']} {f['normalized_unit']}\n"
            f"Period: {f['period']} | Normalized Period: {f['normalized_period']}\n"
            f"Context: {f['context']}\n"
            f"Evidence: \"{f['evidence_sentence']}\"\n"
        )

    user_prompt = "Examine the following related facts and compare the pairs:\n\n" + "\n---\n".join(facts_summary)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        raw_json = json.loads(response.choices[0].message.content)
        validated = CrossDocumentAnalysis(**raw_json)
        comparisons = [c.model_dump() for c in validated.comparisons]
        
        _store_relationships(comparisons)
        return comparisons
    except Exception as e:
        print(f"Error during cross-document reasoning: {e}")
        return []

def _store_relationships(comparisons: List[Dict[str, Any]]):
    """Persists the computed relationships to avoid re-evaluating on every request."""
    if not comparisons:
        return
        
    conn = sqlite3.connect("knowledge_layer.db")
    cursor = conn.cursor()
    
    query = """
        INSERT INTO relationships (fact_a_id, fact_b_id, relationship, dimension, reasoning, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    records = [
        (
            c['fact_a_id'], c['fact_b_id'], c['relationship'], 
            c.get('dimension'), c['reasoning'], c['confidence']
        ) for c in comparisons
    ]
    
    cursor.executemany(query, records)
    conn.commit()
    conn.close()
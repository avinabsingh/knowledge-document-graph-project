import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# Use the model verified in Step 2
MODEL_NAME = "openai/gpt-oss-120b"

class FactComparisonResult(BaseModel):
    relationship: str = Field(
        description="Must be strictly one of: 'CORROBORATION', 'CONTRADICTION', 'RECONCILED_BY_CONTEXT', or 'UNRELATED'"
    )
    explanation: str = Field(
        description="Detailed logical reasoning explaining why this classification was chosen."
    )
    reconciliation_dimension: Optional[str] = Field(
        description="If reconciled, specify dimension: 'Time/Period', 'Scope/Geography', 'Units/Scale', 'Accounting Method', or 'None'",
        default=None
    )
    fact_a_id: int = Field(description="Database ID of the first fact")
    fact_b_id: int = Field(description="Database ID of the second fact")

class CrossDocumentAnalysis(BaseModel):
    comparisons: List[FactComparisonResult]

def compare_fact_cluster(cluster: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes a cluster of facts sharing the same entity and metric across different documents.
    Prompts the LLM to cross-examine each pair and classify the relationship.
    """
    if len(cluster) < 2:
        return []

    system_prompt = (
        "You are an expert investigative auditor and forensic document analyst. "
        "You are comparing facts extracted from multiple corporate filings. "
        "Classify how these facts relate across documents into one of these categories:\n"
        "1. 'CORROBORATION': The facts reinforce or confirm each other.\n"
        "2. 'CONTRADICTION': Genuine direct factual clash.\n"
        "3. 'RECONCILED_BY_CONTEXT': Apparent contradiction resolved by temporal differences, "
        "scope differences, or unit differences.\n"
        "4. 'UNRELATED': The facts discuss different metrics and cannot be compared.\n\n"
        "You MUST reply with a JSON object containing a 'comparisons' array adhering to this schema:\n"
        "{\n"
        '  "comparisons": [\n'
        "    {\n"
        '      "relationship": "CORROBORATION" | "CONTRADICTION" | "RECONCILED_BY_CONTEXT" | "UNRELATED",\n'
        '      "explanation": "Detailed logical reasoning",\n'
        '      "reconciliation_dimension": "Time/Period" | "Scope/Geography" | "Units/Scale" | "None" | null,\n'
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
            f"Source Document: {f['source_filename']} (Page {f['page_number']})\n"
            f"Entity: {f['entity']}\n"
            f"Metric: {f['metric_or_attribute']}\n"
            f"Value: {f['value']}\n"
            f"Context: {f['context']}\n"
            f"Evidence: \"{f['source_sentence']}\"\n"
        )

    user_prompt = (
        "Examine the following related facts extracted from different documents and compare the pairs:\n\n"
        + "\n---\n".join(facts_summary)
    )

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
        return [c.model_dump() for c in validated.comparisons]
    except Exception as e:
        print(f"Error during cross-document reasoning: {e}")
        return []


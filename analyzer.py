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

MODEL_NAME = "openai/gpt-oss-120b" # Using a highly capable model for strict JSON

class Fact(BaseModel):
    # Adding defaults ensures Pydantic NEVER crashes if the LLM skips a field during dense table parsing
    category: str = Field(default="Financial", description="E.g., Financial, Operational")
    entity: str = Field(default="Delhivery", description="The organization, company, or entity")
    metric: str = Field(description="The specific metric or attribute (e.g., Total Revenue)")
    raw_value: Optional[str] = Field(default=None, description="The exact value as stated")
    raw_unit: Optional[str] = Field(default=None, description="The original unit")
    normalized_value: Optional[float] = Field(default=None, description="Numeric value extracted")
    normalized_unit: Optional[str] = Field(default=None, description="Normalized unit")
    period: Optional[str] = Field(default=None, description="The time period")
    normalized_period: Optional[str] = Field(default=None, description="Normalized period")
    context: str = Field(default="Extracted from table or document.", description="Context")
    evidence_sentence: str = Field(default="Data found in table/text.", description="Exact quote")
    evidence_text: str = Field(default="Data found in table/text.", description="Surrounding text")
    confidence: float = Field(default=0.8, description="Confidence score 0.0 to 1.0")
    extraction_notes: Optional[str] = Field(default=None, description="Notes on ambiguity")

class FactList(BaseModel):
    facts: List[Fact]

def extract_facts(chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts facts from a text chunk and normalizes them via LLM."""
    system_prompt = (
        "You are an expert financial and data analyst. Extract key facts, metrics, and attributes from the text. "
        "Adhere strictly to the JSON schema provided. Do not skip fields.\n"
        "NORMALIZATION RULES:\n"
        "- Currency/Numbers: '₹7,241 Cr' -> raw_value='₹7,241 Cr', normalized_value=7241.0, normalized_unit='crore INR'.\n"
        "- Percentages: '5%' -> normalized_value=5.0, normalized_unit='percent'.\n"
        "- Periods: 'FY22', '2021-22' -> normalized_period='FY2022'.\n"
        "CRITICAL: You MUST output a JSON object with a single root key called 'facts' containing a list of objects. "
        "Every object MUST have 'metric', 'category', 'entity', 'raw_value', 'period', 'context', and 'evidence_sentence'."
    )
    
    user_prompt = (
        f"Document: {chunk['filename']}\n"
        f"Pages: {chunk['page_start']} to {chunk['page_end']}\n"
        f"Chunk ID: {chunk['chunk_id']}\n\n"
        f"Text to analyze:\n{chunk['text']}"
    )
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        raw_json = json.loads(response.choices[0].message.content)
        
        # --- RESILIENCE LAYER ---
        if isinstance(raw_json, list):
            raw_json = {"facts": raw_json}
        elif "metrics" in raw_json and "facts" not in raw_json:
            raw_json["facts"] = raw_json.pop("metrics")
        elif "facts" not in raw_json:
            for key, value in list(raw_json.items()):
                if isinstance(value, list):
                    raw_json = {"facts": value}
                    break
        # ------------------------
        
        validated = FactList(**raw_json)
        
        results = []
        for fact in validated.facts:
            fact_dict = fact.model_dump()
            fact_dict['document_id'] = chunk['chunk_id'].split('_chunk_')[0]
            fact_dict['source_filename'] = chunk['filename']
            fact_dict['page_number'] = chunk['page_start']
            fact_dict['chunk_id'] = chunk['chunk_id']
            results.append(fact_dict)
            
        return results
    except Exception as e:
        print(f"Extraction failed for chunk {chunk['chunk_id']}: {e}")
        return []
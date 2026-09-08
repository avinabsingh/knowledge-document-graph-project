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

MODEL_NAME = "openai/gpt-oss-120b"

class Fact(BaseModel):
    category: str = Field(description="E.g., Financial, Operational, Personnel, Macroeconomic")
    entity: str = Field(description="The organization, company, or entity the fact is about")
    metric: str = Field(description="The specific metric or attribute (e.g., Total Revenue, Net Loss)")
    raw_value: Optional[str] = Field(description="The exact value as stated (e.g., '₹7,241 Cr', '5%')")
    raw_unit: Optional[str] = Field(description="The original unit (e.g., 'Cr', 'Million', '%')")
    normalized_value: Optional[float] = Field(description="Numeric value extracted (e.g., 7241.0, 5.0)")
    normalized_unit: Optional[str] = Field(description="Normalized unit (e.g., 'crore INR', 'percent')")
    period: Optional[str] = Field(description="The time period (e.g., 'FY22', '2023-24')")
    normalized_period: Optional[str] = Field(description="Normalized period (e.g., 'FY2022', 'FY2024')")
    context: str = Field(description="Brief context needed to understand the fact")
    evidence_sentence: str = Field(description="The exact single sentence containing this fact")
    evidence_text: str = Field(description="The broader paragraph or surrounding text for context")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    extraction_notes: Optional[str] = Field(description="Any notes on ambiguity or parsing issues")

class FactList(BaseModel):
    facts: List[Fact]

def extract_facts(chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts facts from a text chunk and normalizes them via LLM."""
    system_prompt = (
        "You are an expert financial and data analyst. Extract key facts, metrics, and attributes from the text. "
        "Adhere strictly to the JSON schema provided. "
        "NORMALIZATION RULES:\n"
        "- Currency/Numbers: '₹7,241 Cr' -> raw_value='₹7,241 Cr', normalized_value=7241.0, normalized_unit='crore INR'.\n"
        "- Percentages: '5%' -> normalized_value=5.0, normalized_unit='percent'.\n"
        "- Periods: 'FY22', '2021-22' -> normalized_period='FY2022'.\n"
        "Ensure exact quotes for evidence_sentence and evidence_text."
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
        validated = FactList(**raw_json)
        
        results = []
        for fact in validated.facts:
            fact_dict = fact.model_dump()
            # Inject chunk routing metadata
            fact_dict['document_id'] = chunk['chunk_id'].split('_chunk_')[0]
            fact_dict['source_filename'] = chunk['filename']
            fact_dict['page_number'] = chunk['page_start']
            fact_dict['chunk_id'] = chunk['chunk_id']
            results.append(fact_dict)
            
        return results
    except Exception as e:
        print(f"Extraction failed for chunk {chunk['chunk_id']}: {e}")
        return []
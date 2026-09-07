import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Read Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Check if API key exists
if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY not found! Create a .env file with:\n"
        "GROQ_API_KEY=gsk_your_actual_groq_api_key"
    )

# Initialize Groq client (OpenAI-compatible)
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# Groq model
MODEL_NAME = "openai/gpt-oss-120b"

# -------------------- Pydantic Schema -------------------- #

class Fact(BaseModel):
    category: str = Field(
        description="Financial, Operational, Personnel, or Macroeconomic"
    )
    entity: str = Field(description="Main entity this fact is about")
    metric_or_attribute: str = Field(description="Metric or property being described")
    value: Optional[str] = Field(default=None)
    context: str = Field(description="Time period or scope")
    source_sentence: str = Field(description="Supporting sentence from the document")
    source_filename: str = Field(description="Document filename")
    page_number: int = Field(description="Source page number")


class FactList(BaseModel):
    facts: List[Fact]


# -------------------- Fact Extraction -------------------- #

def extract_facts(chunk: dict) -> List[dict]:
    """
    Extract structured facts from one PDF chunk using Groq.
    """

    system_prompt = """
You are an expert fact extraction engine.

Extract only concrete facts from the document text.

Rules:
- Extract financial, operational, personnel, and macroeconomic facts.
- Preserve exact numbers, units, dates, and fiscal years.
- Ignore legal boilerplate, headers, footers, and table of contents.
- Every fact must include the supporting sentence from the text.

Return ONLY valid JSON in this format:

{
  "facts": [
    {
      "category": "Financial",
      "entity": "Delhivery",
      "metric_or_attribute": "Revenue",
      "value": "₹7,241 Cr",
      "context": "FY2022",
      "source_sentence": "...",
      "source_filename": "...",
      "page_number": 18
    }
  ]
}
"""

    user_prompt = f"""
Source Document: {chunk['filename']}
Page Number: {chunk['page_number']}

Text:
{chunk['text']}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        validated = FactList(**data)

        return [fact.model_dump() for fact in validated.facts]

    except Exception as e:
        print(
            f"❌ Extraction failed on {chunk['filename']} page {chunk['page_number']}"
        )
        print("Reason:", e)
        return []
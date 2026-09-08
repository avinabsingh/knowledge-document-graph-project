# Fact Knowledge Layer

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018-61DAFB?style=flat-square&logo=react)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Bundler-Vite-646CFF?style=flat-square&logo=vite)](https://vitejs.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat-square&logo=sqlite)](https://www.sqlite.org/)
[![Groq](https://img.shields.io/badge/LLM%20Engine-Groq%20API-F55036?style=flat-square)](https://groq.com/)

A production-grade AI system designed to ingest corporate PDF filings, extract normalized financial and operational facts, link them into an interactive Semantic Knowledge Graph, and perform automated cross-document conflict detection and contextual reasoning.

Built for the **Superjoin Engineering Intern Assignment**.

---

## Overview

Traditional Retrieval-Augmented Generation (RAG) pipelines struggle with comparative analysis across multi-year filings because metrics often differ due to temporal drift, accounting methodologies, or differing scopes (e.g., Standalone vs. Consolidated).

The **Fact Knowledge Layer** bypasses naive semantic search by turning raw unstructured text and tables into strongly typed, normalized atomic facts. It automates:

1. **Generic PDF ingestion & deduplication** using SHA-256 document hashing.
2. **Resilient schema-enforced extraction** with Pydantic v2 and LLM fallback heuristics.
3. **Fuzzy semantic clustering** to connect cross-document metrics despite corporate suffix or naming drift.
4. **Automated cross-document reasoning** to detect factual corroborations, direct contradictions, and context-reconciled discrepancies.
5. **Interactive UI exploration** featuring a force-directed knowledge graph and click-to-inspect evidence modals.

---

## System Architecture

```text
[ Raw PDF Uploads ]
        │
        ▼
[ PyMuPDF Parser & Semantic Chunker ] ─── (Sliding window with token overlap)
        │
        ▼
[ LLM Fact Extractor (Groq / gpt-oss-120b) ]
        │
        ▼
[ Resilience Layer & Pydantic Sanitizer ] ─── (Self-healing JSON parsing)
        │
        ▼
[ SQLite Relational Storage ] ─── (Documents, Facts, Relationships, Failures)
        │
        ▼
[ Fuzzy Semantic Clusterer ] ─── (difflib SequenceMatcher & Token Intersection)
        │
        ▼
[ Cross-Document Reasoner Engine ] ─── (Corroboration, Contradiction, Reconciliation)
        │
        ▼
[ React + ForceGraph2D Interface ] ─── (Interactive Graph + Evidence Grounding Modal)
```

---

## Core Capabilities

- **Document Registry & Deduplication** — Generates cryptographic SHA-256 hashes per document to prevent redundant LLM extraction cycles and duplicate database insertions.
- **Extraction Resilience Layer** — Pre-processes volatile LLM JSON responses to resolve root-key hallucinations (e.g., returning `"metrics"` instead of `"facts"`, or raw lists) while applying default fallbacks for dense table entries.
- **Fuzzy Semantic Clustering** — Implements a multi-pass normalization pipeline using Python's `difflib.SequenceMatcher` and token-set overlap to pair related metrics across filings without requiring exact string equality.
- **Four-Tiered Cross-Document Reasoning:**
  - **Corroboration** — Identical metrics and periods across documents that confirm historical data.
  - **Contradiction** — Direct factual clashes where scope and timeframe match but values diverge.
  - **Reconciled by Context** — Conflicting numbers resolved along explicit dimensions (time, scope, units, accounting method).
  - **Failure Handling** — Ambiguous or low-confidence extractions flagged and routed to `extraction_failures` for auditability.
- **Source-Grounding UI** — Every fact retains chunk IDs, page indices, and verbatim source sentences, viewable inside an interactive detail modal.

---

## Repository Structure

```text
knowledge-layer/
├── backend/
│   ├── app.py               # FastAPI application & REST route definitions
│   ├── analyzer.py          # LLM extraction prompts, Pydantic models & resilience layer
│   ├── reasoner.py          # Cross-document auditor & comparison logic
│   ├── storage.py           # SQLite schemas, CRUD queries & fuzzy clustering
│   ├── parser.py            # PyMuPDF text & table extraction pipeline
│   └── requirements.txt     # Python dependency specifications
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Dashboard, 4-case showcase, graph & fact tables
│   │   ├── main.jsx         # React application entrypoint
│   │   └── index.css        # Global layout styling
│   ├── package.json         # Node runtime dependencies & scripts
│   └── vite.config.js       # Vite bundler configuration
├── .env.example              # Environment configuration template
├── .gitignore                 # Ignored runtime artifacts & keys
└── README.md                  # Project documentation
```

---

## Database Schema

```sql
-- Document Registry
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    page_count INTEGER,
    chunk_count INTEGER,
    processing_status TEXT DEFAULT 'pending'
);

-- Atomic Facts
CREATE TABLE facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    category TEXT NOT NULL,
    entity TEXT NOT NULL,
    metric TEXT NOT NULL,
    raw_value TEXT,
    raw_unit TEXT,
    normalized_value REAL,
    normalized_unit TEXT,
    period TEXT,
    normalized_period TEXT,
    context TEXT,
    evidence_sentence TEXT NOT NULL,
    evidence_text TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    chunk_id TEXT NOT NULL,
    confidence REAL,
    extraction_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

-- Cross-Document Relationships
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_a_id INTEGER NOT NULL,
    fact_b_id INTEGER NOT NULL,
    relationship TEXT NOT NULL, -- CORROBORATION, CONTRADICTION, RECONCILED_BY_CONTEXT
    dimension TEXT,             -- time, scope, units, accounting_method
    reasoning TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fact_a_id) REFERENCES facts(id),
    FOREIGN KEY(fact_b_id) REFERENCES facts(id)
);

-- Extraction Failures Log
CREATE TABLE extraction_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    original_evidence TEXT,
    attempted_extraction TEXT,
    reason TEXT,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- A Groq Cloud API key

### Backend Setup

Open a terminal and navigate to the project root:

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux/macOS
source venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=openai/gpt-oss-120b
DATABASE_PATH=knowledge_layer.db
```

Initialize the database tables:

```bash
python -c "from storage import init_db; init_db()"
```

Start the FastAPI development server:

```bash
uvicorn app:app --reload --port 8000
```

### Frontend Setup

In a separate terminal window, navigate to the frontend directory:

```bash
cd frontend
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Open your browser and navigate to **http://localhost:5173**.

---

## API Reference

| Method | Endpoint    | Description |
|--------|-------------|--------------|
| POST   | `/upload`   | Accepts multipart PDF upload, hashes file, chunks text, extracts facts, and populates database. |
| GET    | `/facts`    | Returns all extracted facts with complete normalization and grounding metadata. |
| GET    | `/analyze`  | Triggers fuzzy cluster grouping and executes LLM cross-document reasoning. |
| GET    | `/documents`| Lists all registered documents and ingestion statuses. |

---

## Assignment Demonstration Cases

| Case | Scenario | Engine Behavior |
|------|----------|------------------|
| **1. Corroboration** | Historical revenue or static metadata (e.g., CIN, address) reported identically across filings. | Matches facts across distinct filings; verifies numerical/semantic alignment; tags `CORROBORATION`. |
| **2. Contradiction** | Conflicting governance facts or misaligned historical figures for the same scope and fiscal period. | Flags irreconcilable factual discrepancies for identical parameters; tags `CONTRADICTION`. |
| **3. Reconciled by Context** | Stated values differ between filings due to fiscal timeline growth or Standalone vs. Consolidated reporting. | Detects discrepancies; reconciles using temporal/scope attributes; tags `RECONCILED_BY_CONTEXT` with assigned dimension. |
| **4. Failure Handling** | Poorly structured tables with omitted units or low extraction confidence (<0.70). | Intercepts malformed data through the resilience layer; routes records to `extraction_failures`. |

---

## Engineering Trade-offs & Future Roadmap

**In-Memory Fuzzy Clustering vs. Vector Embeddings**
- *Current:* Uses string distance (`difflib`) and corporate suffix regex cleaning. This minimizes overhead and eliminates the need for heavyweight external vector databases.
- *Future:* Integrate dense vector embeddings (e.g., `BAAI/bge-large-en` or `sentence-transformers`) with an embedded vector store (ChromaDB) to capture subtle semantic equivalences (e.g., "Capex" vs. "Purchase of property, plant, and equipment").

**Synchronous Processing vs. Async Job Queues**
- *Current:* Chunks are processed sequentially with rate-limit delays to stay within free-tier API quotas.
- *Future:* Transition ingestion tasks to an asynchronous Celery/Redis queue with Celery Beat to enable horizontal scale, worker concurrency, and resilient task retries.

**Standard PDF Text Parsing vs. Layout-Aware Vision Models**
- *Current:* Parses text via PyMuPDF. Highly performant, but occasionally flattens complex multi-span financial balance sheets into raw lines.
- *Future:* Introduce a vision-language OCR pipeline (such as LayoutLMv3 or Claude Vision) specifically for tabular pages.

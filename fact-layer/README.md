# Fact Knowledge Layer

A system for extracting, grounding, and cross-referencing facts from PDF documents using LLMs, vector search, and structured storage.

## Features

- **PDF Processing**: Extract text and tables with precise character-level location tracking
- **Concurrent Fact Extraction**: LLM-powered extraction running chunks in parallel (semaphore-controlled, 3× faster on large PDFs)
- **Evidence Grounding**: Every fact is pinned to its exact `char_start`/`char_end` offset and raw source text
- **Cross-Document Analysis**: Detect corroborations, contradictions, and context-explained reconciliations
- **Incremental Processing**: New documents are compared only against existing facts — no full rebuild required
- **Semantic Search**: ChromaDB vector store (`all-MiniLM-L6-v2`) enables meaning-based search across all facts
- **API + UI**: FastAPI backend with a Streamlit UI (5 tabs: Upload, Fact Explorer, Relationships, Search, Demo Cases)

---

## Quick Start

### 1. Install Dependencies

```bash
cd fact-layer
pip install -r requirements.txt
```

> **Note:** On first run, ChromaDB will download the `all-MiniLM-L6-v2` ONNX embedding model (~79 MB, one-time, cached permanently).

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your API key:

```bash
cp .env.example .env
# Edit .env — set NVIDIA_API_KEY and EXTRACTOR_TYPE=nvidia
```

For testing without an API key, leave `EXTRACTOR_TYPE=mock` (default). The mock extractor uses pattern-based extraction and works with all other features.

### 3. Process Starter Data

```bash
python process_starter_data.py
```

This processes all 6 PDFs in the starter datasets, extracts facts with evidence, and runs cross-document relationship analysis.

### 4. (Optional) Backfill Semantic Search Index

If you already have facts in the database from a previous run:

```bash
python backfill_chroma.py
```

New documents uploaded after step 3 are indexed automatically — this script is only needed for pre-existing data.

### 5. Start the API

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

### 6. Start the Streamlit UI

```bash
streamlit run ui/streamlit_app.py --server.port 8501
```

UI available at http://localhost:8501

---

## Project Structure

```
fact-layer/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings (env-driven)
│   ├── database.py          # SQLAlchemy + SQLite setup
│   ├── models.py            # ORM models: Document, Fact, FactRelationship
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── vector_store.py      # ChromaDB singleton (semantic search)
│   ├── pdf/                 # PDF parsing + chunking
│   ├── extraction/          # LLM extractors, prompts, validator, normalizer
│   ├── analysis/            # Cross-document relationship detection
│   ├── api/                 # FastAPI route handlers
│   └── services/            # Async processing pipeline
├── ui/
│   └── streamlit_app.py     # Streamlit UI (5-tab interface)
├── data/                    # Uploads, SQLite DB, ChromaDB store
├── process_starter_data.py  # Batch processing script for starter PDFs
├── backfill_chroma.py       # One-time script to index existing facts in ChromaDB
└── requirements.txt
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/documents/upload` | Upload a PDF — triggers async processing |
| `GET /api/documents` | List all documents with status |
| `GET /api/documents/{id}/status` | Poll processing status |
| `GET /api/documents/{id}/facts` | Browse extracted facts (filterable by type, confidence) |
| `DELETE /api/documents/{id}` | Delete document, facts, relationships, and Chroma vectors |
| `GET /api/facts/{id}` | Get a single fact with full evidence |
| `GET /api/relationships` | List cross-document relationships (filter by type) |
| `GET /api/relationships/{id}/evidence` | Full side-by-side evidence for a relationship |
| `GET /api/entities/{name}/facts` | All facts for an entity across documents |
| `POST /api/search` | Keyword search over facts |
| `POST /api/search/semantic` | **Vector search** — find facts by meaning, not keywords |
| `POST /api/analyze/relationships` | Manually trigger full relationship re-analysis |
| `GET /api/cases` | The four required demo cases, auto-selected by quality |
| `GET /api/stats` | System statistics (documents, facts, relationships) |

---

## Starter Datasets

- **delhivery**: Prospectus 2022, Annual Report FY24, Q4 FY24 Earnings
- **india-macroeconomy**: Economic Survey 2024-25, RBI Annual Report 2024-25, IMF Article IV 2025

---

## Demo Cases

The **Cases** tab in the UI shows all four required cases with source evidence:

1. **Corroboration** — The same fact confirmed across documents, even if expressed differently (e.g., GDP growth rate appearing in both the Economic Survey and the RBI Annual Report)
2. **Contradiction** — A genuine conflict: two documents report materially different values for the same metric and period
3. **Reconciliation** — Values differ, but the system's LLM call explains the difference by context (different time period, scope, or unit)
4. **Extraction Failure** — A documented failure mode with how it was handled and what would be improved

---

## Architecture

```
PDF
 │
 ▼
PDFParser + Chunker
 │
 ▼  (chunks processed concurrently — asyncio.gather + semaphore)
LLM Extractor  ──────────────────────────────────────────────────┐
 │                                                                │
 ▼  (checkpoint every 10 pages — crash-safe, resumable)         │
SQLite (Documents, Facts, Relationships)                         │
 │                                                                │
 ├──► ChromaDB (vector embeddings — auto-indexed per fact)       │
 │         └── POST /search/semantic                             │
 │                                                                │
 ▼  (incremental — only new facts compared against existing)     │
RelationshipDetector (corroborates / contradicts / reconciles) ◄─┘
 │
 ▼
FastAPI  ◄──►  Streamlit UI
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **SQLite as primary store** | Zero setup, portable, sufficient for prototype scale |
| **ChromaDB as search index** | Additive to SQLite — failures are non-fatal, SQLite is always source of truth |
| **Concurrent chunk extraction** | `asyncio.gather` per 10-page window, bounded by semaphore — 3× faster vs. serial |
| **Incremental relationship detection** | New documents compare only against existing facts, not the full corpus |
| **Page-level checkpointing** | Every 10-page window committed to SQLite — interrupted jobs resume from last checkpoint |
| **LLM reconciliation** | When numeric values differ >5%, an LLM call decides: true contradiction or context difference |

---

## Configuration

Key settings in `.env` (see `.env.example` for full list):

| Variable | Default | Description |
|---|---|---|
| `NVIDIA_API_KEY` | — | API key for NVIDIA Nemotron extraction |
| `EXTRACTOR_TYPE` | `mock` | `nvidia` / `ollama` / `mock` |
| `DATABASE_URL` | `sqlite:///./data/fact_layer.db` | SQLite path |
| `CHROMA_DIR` | `./data/chroma` | ChromaDB persistence directory |
| `CHUNK_MAX_TOKENS` | `3000` | Max tokens per extraction chunk |
| `MAX_CONCURRENT_EXTRACTIONS` | `3` | Parallel LLM calls per window |

---

# Developer's Section

## Setup and Run Instructions

*See the **Quick Start** section above. The full sequence is:*

```bash
pip install -r requirements.txt          # 1. Install deps
cp .env.example .env                     # 2. Configure
python process_starter_data.py           # 3. Process starter PDFs
python backfill_chroma.py                # 4. Index into ChromaDB
uvicorn app.main:app --reload --port 8000   # 5. Start API
streamlit run ui/streamlit_app.py --server.port 8501  # 6. Start UI
```

## Video Demo

![System Demo Recording](demo.webp)

---

## Approach

### Architecture & Important Decisions

**Extraction pipeline:**
The system chunks each PDF (max 3,000 tokens per chunk) and sends chunks to an LLM for structured fact extraction. Each extracted fact includes `entity`, `attribute`, `value`, `unit`, `time_period`, `scope`, `qualifier`, `confidence`, and a character-level evidence span.

Chunks within a 10-page window are processed **concurrently** using `asyncio.gather`, controlled by an `asyncio.Semaphore` (default: 3 parallel calls). This makes large PDFs ~3× faster than serial processing. Every 10-page window is committed to SQLite as a checkpoint — if processing is interrupted, it resumes from the last completed page.

**Evidence grounding:**
Every fact records `char_start` and `char_end` within the source chunk, and a `raw_evidence` text slice. The UI renders this evidence verbatim next to every fact and relationship.

**Relationship analysis:**
The `RelationshipDetector` groups facts by normalized entity + attribute. For each cross-document pair in the same time period:
1. If numeric values agree within 5% → `corroborates`
2. If they differ → an LLM call inspects both facts and their evidence to decide: `contradicts` (genuine conflict) or `reconciles` (difference explained by scope, time period, or units)

Analysis is **incremental**: uploading a new document only re-evaluates facts involving that document — the full corpus is not rebuilt.

**Semantic search (ChromaDB):**
Each fact is embedded using `all-MiniLM-L6-v2` (local, no API key). The embedding string packs entity, attribute, value, time period, and evidence so paraphrased queries match. A query like *"Indian economic output"* will return facts labelled *"GDP growth"* because the vector representations are close, even if no keyword overlaps. Chroma is additive — if it's unavailable, the pipeline continues using SQLite only.

**Dynamic schema:**
There are no hard-coded fact types per document. The LLM determines what counts as a fact from context. New document types automatically generate new entity and attribute categories that become immediately searchable via ChromaDB embeddings.

### AI Tools Used

- **NVIDIA Nemotron Super 49B** — core fact extraction and reconciliation logic via the NVIDIA API
- **AI coding assistants** — scaffolding FastAPI/Streamlit boilerplate, database models, and concurrent pipeline refactoring

---

## Limitations and Next Steps

### Known Limitations

- **Table parsing:** Complex financial tables spanning multiple pages sometimes confuse the chunker, leading to attributes assigned to the wrong columns or years. The mock extractor is especially affected.
- **Entity resolution:** Normalization uses string similarity (`SequenceMatcher`). Highly paraphrased entity names that don't share tokens may not merge correctly.
- **Relationship false positives:** When two documents report the same metric for different sub-periods that both map to the same year token, the comparator may incorrectly classify them as contradictions.
- **ChromaDB cold start:** On first use, ChromaDB downloads the embedding model (~79 MB). This adds ~2 minutes to the very first extraction batch.

### What I Would Build Next

- **Two-pass agentic extraction:** A first LLM pass identifies the document's structure (table of contents, section headers, table boundaries) and the second pass extracts facts with full structural context — dramatically reducing table mis-attribution.
- **Celery / Redis background queue:** Replace FastAPI's `BackgroundTasks` with a proper task queue for production-scale concurrency and retry logic.
- **Graph-based relationship store:** Migrate `FactRelationship` to a native graph structure (e.g., NetworkX or Neo4j) for multi-hop queries like *"show all facts that contradict anything corroborated by document X"*.
- **Streaming extraction progress:** Push real-time progress via WebSocket instead of polling the `/jobs` endpoint.

---

## Explanation of an Extraction Failure (Case 4)

**The failure:** During testing with financial documents, the LLM sometimes extracted a generic `"Profit"` attribute without clarifying whether it was *Profit Before Tax* or *Profit After Tax*. This caused a false contradiction when the two were compared across documents that correctly labelled them separately.

**How it was handled:** The extraction prompt was updated to require granular attribute names (prefer `"Profit Before Tax"` over `"Profit"`) and to use the `qualifier` field to capture the surrounding table header context. A `validator.py` post-processing step also filters out facts whose attribute is in a known ambiguity list.

**Future improvement:** A validation pass that detects over-generic attributes and re-submits those chunks to the LLM with an explicit disambiguation prompt.

---

## Additional Notes

- The `MockExtractor` in `extractor.py` uses pattern-based regex extraction for testing without an API key. All other system features (ChromaDB, relationships, search, UI) work fully with the mock extractor.
- The `backfill_chroma.py` script is safe to re-run — ChromaDB upserts are idempotent.
- Credentials are never stored in the repository. All secrets are loaded from `.env` which is gitignored.
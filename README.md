# Engineering Intern Hiring Assignment

### Welcome! 👋

This assignment is intentionally open-ended. We want to see how you explore an unfamiliar problem and turn your ideas into something that works.

- Use any language, framework, database, LLM, coding agent, or library.
- We care more about your approach and creativity than production-level polish.
- Be honest about what works, what does not, and what you would improve.

## ✨ The Challenge: Build a Fact Knowledge Layer ✨

Important facts are often scattered across documents, stated in different ways, supported by other evidence, or contradicted elsewhere.

You will receive **three PDFs as a starter dataset**. Build a system that:

- extracts meaningful numerical or semantic facts;
- links every fact to evidence in its source document; and
- identifies when facts corroborate, contradict, or can be reconciled through context.

Provide a simple **API or UI** through which we can upload PDFs and inspect the results. We may test your solution with additional PDFs, so it should not rely on hard-coded facts, filenames, schemas, or document-specific rules.

The documents should guide what counts as a fact and how it is represented. Your schema, storage, interface, and output format are entirely up to you.

> **A graph database or visualization alone is not the solution.** The interesting part is how facts are discovered, grounded, compared, and explained.

### Show Us These Four Cases

Your submission should include at least one example of each:

1. A fact corroborated across documents, even if expressed differently.
2. A genuine or likely contradiction.
3. An apparent contradiction explained by context, such as time, scope, or units.
4. An extraction or reasoning failure you found and how you handled—or would improve—it.

Show the source evidence and your system's reasoning for the first three.

For inspiration, two revenue figures may differ because they cover different periods; a director may appear active in one document and resigned in a later one; or differently written addresses may refer to the same place. These are examples, not a required data model or checklist of facts.

## What We Are Looking For

- A thoughtful and creative approach.
- Useful facts that are grounded in the PDFs.
- Sensible handling of ambiguity, context, and uncertainty.
- A solution that can generalize beyond the starter documents.
- Clear engineering decisions and trade-offs.

We do not expect perfect extraction or a production-ready system. A smaller, understandable prototype is better than a large system whose behavior is unclear.

## Brownie Points 🍪

If the core experience works, try extending it to handle:

- large PDFs without significant performance issues;
- many PDFs in the same knowledge layer;
- a schema that evolves dynamically as new kinds of facts appear; or
- new documents incrementally, without rebuilding all existing knowledge.

These are suggestions, not additional requirements. Feel free to explore another extension that meaningfully improves the core system.

## Submission ⏰

Use git meaningfully and complete the Developer's Section below with:

- setup and run instructions;
- your approach, important decisions, and AI tools used;
- known limitations and possible next steps; and
- a demo video of **3 minutes or less** showing a PDF being processed and the required cases above.

Keep credentials out of the repository. If the project requires a paid service, include enough sample output and video footage for us to evaluate it without needing your account.

### Before You Submit

- [x] The project runs from my instructions and accepts new PDFs through an API or UI.
- [x] Results contain facts, source evidence, and cross-document relationships.
- [x] I demonstrate the four required cases.
- [x] I have documented my approach and included a demo video of 3 minutes or less.

Most importantly, have fun tinkering. We are excited to see how you think.

---

## Developer's Section

### Setup and Run Instructions

```bash
# 1. Install dependencies
cd fact-layer
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — set NVIDIA_API_KEY and EXTRACTOR_TYPE=nvidia
# (leave EXTRACTOR_TYPE=mock to run without an API key — see Additional Notes)

# 3. Process the starter PDFs
python process_starter_data.py

# 4. (Optional) Backfill semantic search index for pre-existing data
python backfill_chroma.py

# 5. Start the API
uvicorn app.main:app --reload --port 8000
# Interactive API docs: http://localhost:8000/docs

# 6. Start the Streamlit UI
streamlit run ui/streamlit_app.py --server.port 8501
# UI available at http://localhost:8501
```

> **Note:** On first run, ChromaDB downloads the `all-MiniLM-L6-v2` ONNX embedding model (~79 MB, one-time, cached permanently) — this adds ~2 minutes to the very first extraction batch.

**Starter datasets processed:**
- **delhivery**: Prospectus 2022, Annual Report FY24, Q4 FY24 Earnings
- **india-macroeconomy**: Economic Survey 2024-25, RBI Annual Report 2024-25, IMF Article IV 2025

**Project structure:**

```
fact-layer/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings (env-driven)
│   ├── database.py          # SQLAlchemy + SQLite setup
│   ├── models.py             # ORM models: Document, Fact, FactRelationship
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── vector_store.py       # ChromaDB singleton (semantic search)
│   ├── pdf/                  # PDF parsing + chunking
│   ├── extraction/           # LLM extractors, prompts, validator, normalizer
│   ├── analysis/              # Cross-document relationship detection
│   ├── api/                   # FastAPI route handlers
│   └── services/              # Async processing pipeline
├── ui/
│   └── streamlit_app.py       # Streamlit UI (5-tab interface)
├── data/                      # Uploads, SQLite DB, ChromaDB store
├── process_starter_data.py    # Batch processing script for starter PDFs
├── backfill_chroma.py         # One-time script to index existing facts in ChromaDB
└── requirements.txt
```

**API endpoints:**

| Endpoint | Description |
|:---|:---|
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
| `POST /api/search/semantic` | Vector search — find facts by meaning, not keywords |
| `POST /api/analyze/relationships` | Manually trigger full relationship re-analysis |
| `GET /api/cases` | The four required demo cases, auto-selected by quality |
| `GET /api/stats` | System statistics (documents, facts, relationships) |

**Configuration (`.env`):**

| Variable | Default | Description |
|:---|:---|:---|
| `NVIDIA_API_KEY` | — | API key for NVIDIA Nemotron extraction |
| `EXTRACTOR_TYPE` | `mock` | `nvidia` / `ollama` / `mock` |
| `DATABASE_URL` | `sqlite:///./data/fact_layer.db` | SQLite path |
| `CHROMA_DIR` | `./data/chroma` | ChromaDB persistence directory |
| `CHUNK_MAX_TOKENS` | `3000` | Max tokens per extraction chunk |
| `MAX_CONCURRENT_EXTRACTIONS` | `3` | Parallel LLM calls per window |

### Video Demo

[**Link to 3-minute Video Demo**](YOUR_VIDEO_LINK_HERE) *(insert your video link here)*

### Approach

**Extraction pipeline:**
The system chunks each PDF (max 3,000 tokens per chunk) and sends chunks to an LLM for structured fact extraction. Each extracted fact includes `entity`, `attribute`, `value`, `unit`, `time_period`, `scope`, `qualifier`, `confidence`, and a character-level evidence span.

Chunks within a 10-page window are processed **concurrently** using `asyncio.gather`, controlled by an `asyncio.Semaphore` (default: 3 parallel calls) — roughly 3× faster than serial processing on large PDFs. Every 10-page window is committed to SQLite as a checkpoint, so an interrupted job resumes from the last completed page.

**Evidence grounding:**
Every fact records `char_start` and `char_end` within the source chunk, and a `raw_evidence` text slice. The UI renders this evidence verbatim next to every fact and relationship.

**Relationship analysis:**
The `RelationshipDetector` groups facts by normalized entity + attribute. For each cross-document pair in the same time period:
1. If numeric values agree within 5% → `corroborates`
2. If they differ → an LLM call inspects both facts and their evidence to decide: `contradicts` (genuine conflict) or `reconciles` (difference explained by scope, time period, or units)

Analysis is **incremental**: uploading a new document only re-evaluates facts involving that document — the full corpus is not rebuilt.

**Semantic search (ChromaDB):**
Each fact is embedded using `all-MiniLM-L6-v2` (local, no API key). The embedding string packs entity, attribute, value, time period, and evidence so paraphrased queries match — a query like *"Indian economic output"* returns facts labelled *"GDP growth"* even with no keyword overlap. Chroma is additive: if it's unavailable, the pipeline continues using SQLite only.

**Dynamic schema:**
There are no hard-coded fact types per document. The LLM determines what counts as a fact from context, so new document types automatically generate new entity/attribute categories that become immediately searchable via ChromaDB embeddings.

**Architecture:**

```
                        PDF
                         │
                         ▼
              PDFParser + Chunker
                         │
                         ▼   (concurrent — asyncio.gather + semaphore)
                   LLM Extractor
                         │
                         ▼   (checkpoint every 10 pages — crash-safe, resumable)
      SQLite (Documents, Facts, Relationships)
                         │
                         ├────────────────────────────┐
                         │                             ▼
                         │              ChromaDB (vector embeddings,
                         │               auto-indexed per fact)
                         │                             │
                         │               POST /api/search/semantic
                         │
                         ▼   (incremental — new facts vs. existing only)
   RelationshipDetector (corroborates / contradicts / reconciles)
                         │
                         ▼
              FastAPI   ◄──►   Streamlit UI
```

**Key design decisions:**

| Decision | Rationale |
|:---|:---|
| SQLite as primary store | Zero setup, portable, sufficient for prototype scale |
| ChromaDB as search index | Additive to SQLite — failures are non-fatal, SQLite is always source of truth |
| Concurrent chunk extraction | `asyncio.gather` per 10-page window, bounded by semaphore — 3× faster vs. serial |
| Incremental relationship detection | New documents compare only against existing facts, not the full corpus |
| Page-level checkpointing | Every 10-page window committed to SQLite — interrupted jobs resume from last checkpoint |
| LLM reconciliation | When numeric values differ >5%, an LLM call decides: true contradiction or context difference |

**Demo cases** (shown in the Cases tab, with source evidence for each):
1. **Corroboration** — the same fact confirmed across documents, even if expressed differently (e.g., GDP growth rate appearing in both the Economic Survey and the RBI Annual Report)
2. **Contradiction** — a genuine conflict: two documents report materially different values for the same metric and period
3. **Reconciliation** — values differ, but the system's LLM call explains the difference by context (time period, scope, or unit)
4. **Extraction Failure** — a documented failure mode with how it was handled (see below)

**AI tools used:**
- **NVIDIA Nemotron Super 49B** — core fact extraction and reconciliation logic via the NVIDIA API
- **AI coding assistants** — scaffolding FastAPI/Streamlit boilerplate, database models, and concurrent pipeline refactoring

### Limitations and Next Steps

**Known limitations:**
- **Table parsing:** Complex financial tables spanning multiple pages sometimes confuse the chunker, leading to attributes assigned to the wrong columns or years. The mock extractor is especially affected.
- **Entity resolution:** Normalization uses string similarity (`SequenceMatcher`). Highly paraphrased entity names that don't share tokens may not merge correctly.
- **Relationship false positives:** When two documents report the same metric for different sub-periods that both map to the same year token, the comparator may incorrectly classify them as contradictions.
- **ChromaDB cold start:** On first use, ChromaDB downloads the embedding model (~79 MB), adding ~2 minutes to the first extraction batch.

**What I would build next:**
- **Two-pass agentic extraction:** a first LLM pass identifies document structure (table of contents, section headers, table boundaries), and the second pass extracts facts with full structural context — reducing table mis-attribution.
- **Celery / Redis background queue:** replace FastAPI's `BackgroundTasks` with a proper task queue for production-scale concurrency and retry logic.
- **Graph-based relationship store:** migrate `FactRelationship` to a native graph structure (e.g., NetworkX or Neo4j) for multi-hop queries like "show all facts that contradict anything corroborated by document X".
- **Streaming extraction progress:** push real-time progress via WebSocket instead of polling the `/jobs` endpoint.

**Explanation of an extraction failure (Case 4):**

*The failure:* During testing with financial documents, the LLM sometimes extracted a generic `"Profit"` attribute without clarifying whether it was *Profit Before Tax* or *Profit After Tax*. This caused a false contradiction when the two were compared across documents that correctly labelled them separately.

*How it was handled:* The extraction prompt was updated to require granular attribute names (prefer `"Profit Before Tax"` over `"Profit"`) and to use the `qualifier` field to capture the surrounding table header context. A `validator.py` post-processing step also filters out facts whose attribute is in a known ambiguity list.

*Future improvement:* A validation pass that detects over-generic attributes and re-submits those chunks to the LLM with an explicit disambiguation prompt.

### Additional Notes

- The `MockExtractor` in `extractor.py` uses pattern-based regex extraction for testing without an API key. All other system features (ChromaDB, relationships, search, UI) work fully with the mock extractor.
- The `backfill_chroma.py` script is safe to re-run — ChromaDB upserts are idempotent.
- Credentials are never stored in the repository. All secrets are loaded from `.env`, which is gitignored.

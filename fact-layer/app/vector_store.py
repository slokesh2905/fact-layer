"""
app/vector_store.py
-------------------
Thin singleton wrapper around ChromaDB.

Responsibilities:
  - Lazily initialise a persistent Chroma client pointing at config.chroma_dir
  - Upsert facts (SQLAlchemy ORM objects OR plain dicts) into the "facts" collection
  - Semantic search by natural-language query
  - Delete all vectors for a given document_id (keeps Chroma in sync with SQLite)

Embedding model: ChromaDB default (all-MiniLM-L6-v2 via sentence-transformers).
  - Runs locally, no API key required
  - Already pulled in by chromadb >= 0.5.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# Module-level singleton — initialised once on first call to get_vector_store()
_vector_store: Optional["VectorStore"] = None


def get_vector_store() -> "VectorStore":
    """Return the module-level VectorStore singleton, creating it if needed."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


class VectorStore:
    """ChromaDB-backed vector store for fact embeddings."""

    COLLECTION_NAME = "facts"

    def __init__(self) -> None:
        from app.config import settings
        import chromadb

        chroma_path = Path(settings.chroma_dir)
        chroma_path.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(chroma_path))
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            # Default embedding function: all-MiniLM-L6-v2 (sentence-transformers)
            # ChromaDB downloads the model on first use (~90 MB).
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"VectorStore initialised at {chroma_path} "
            f"({self._collection.count()} facts indexed)"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def get_collection(self):
        """Expose the raw collection (useful for health checks / stats)."""
        return self._collection

    def upsert_facts(self, facts: Sequence[Any]) -> None:
        """
        Upsert a batch of facts into Chroma.

        `facts` may be SQLAlchemy Fact ORM objects or plain dicts with the same keys.
        Already-indexed facts are updated (idempotent).
        """
        if not facts:
            return

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for fact in facts:
            fact_id, doc_str, meta = self._fact_to_chroma(fact)
            if fact_id:
                ids.append(fact_id)
                documents.append(doc_str)
                metadatas.append(meta)

        if not ids:
            return

        try:
            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            logger.debug(f"Upserted {len(ids)} facts into Chroma")
        except Exception as e:
            # Never let Chroma errors crash the main pipeline
            logger.error(f"ChromaDB upsert failed: {e}")

    def search(
        self,
        query: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over all indexed facts.

        Returns a list of dicts:
            { "fact_id": str, "score": float, "metadata": dict }
        sorted by descending similarity (1 = identical, 0 = orthogonal).
        """
        total = self._collection.count()
        if total == 0:
            return []

        # Chroma raises if n_results > collection size
        actual_n = min(n_results, total)

        try:
            kwargs: Dict[str, Any] = {
                "query_texts": [query],
                "n_results": actual_n,
                "include": ["distances", "metadatas"],
            }
            if where:
                kwargs["where"] = where

            result = self._collection.query(**kwargs)
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return []

        hits = []
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        metas = result.get("metadatas", [[]])[0]

        for fact_id, distance, meta in zip(ids, distances, metas):
            # Cosine distance ∈ [0, 2]; convert to similarity ∈ [0, 1]
            score = max(0.0, 1.0 - distance)
            hits.append({"fact_id": fact_id, "score": round(score, 4), "metadata": meta})

        return hits

    def delete_by_document(self, document_id: str) -> int:
        """
        Remove all fact vectors belonging to `document_id`.
        Returns the number of vectors deleted.
        """
        try:
            # Fetch IDs that match the document
            results = self._collection.get(
                where={"document_id": document_id},
                include=[],  # only need IDs
            )
            ids_to_delete = results.get("ids", [])
            if ids_to_delete:
                self._collection.delete(ids=ids_to_delete)
                logger.info(
                    f"Deleted {len(ids_to_delete)} Chroma vectors for document {document_id}"
                )
            return len(ids_to_delete)
        except Exception as e:
            logger.error(f"ChromaDB delete failed for {document_id}: {e}")
            return 0

    def count(self) -> int:
        """Total number of indexed facts."""
        try:
            return self._collection.count()
        except Exception:
            return 0

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _fact_to_chroma(fact: Any):
        """
        Convert a Fact ORM object (or dict) into (id, document_string, metadata).

        The document string is what Chroma embeds.  It deliberately packs the
        most semantically meaningful fields so that paraphrased queries
        ("Indian economic expansion") match stored facts ("GDP growth, India").
        """
        # Support both ORM objects and plain dicts
        def _get(key: str, default: Any = "") -> Any:
            if isinstance(fact, dict):
                return fact.get(key, default) or default
            return getattr(fact, key, default) or default

        fact_id: str = str(_get("id", ""))
        if not fact_id:
            return None, "", {}

        entity = _get("entity", "")
        attribute = _get("attribute", "")
        value = _get("value", "")
        unit = _get("unit", "")
        time_period = _get("time_period", "")
        scope = _get("scope", "")
        qualifier = _get("qualifier", "")
        raw_evidence = _get("raw_evidence", "")[:300]
        document_id = str(_get("document_id", ""))
        entity_norm = str(_get("entity_normalized", entity))
        attr_norm = str(_get("attribute_normalized", attribute))
        fact_type = str(_get("fact_type", ""))
        source_dataset = str(_get("source_dataset", ""))

        # Normalise fact_type enum to string
        if hasattr(fact_type, "value"):
            fact_type = fact_type.value  # type: ignore[union-attr]

        # Rich document string for embedding
        doc_str = (
            f"{entity} | {attribute} | {value} {unit} | "
            f"{time_period} | {scope} | {qualifier} | {raw_evidence}"
        ).strip(" |")

        # Flat metadata dict — Chroma only accepts str / int / float / bool values
        metadata: Dict[str, Any] = {
            "document_id": document_id,
            "entity_normalized": entity_norm[:64],
            "attribute_normalized": attr_norm[:64],
            "fact_type": str(fact_type)[:32],
            "time_period": str(time_period)[:32],
            "scope": str(scope)[:32],
            "source_dataset": str(source_dataset)[:64],
        }

        return fact_id, doc_str, metadata

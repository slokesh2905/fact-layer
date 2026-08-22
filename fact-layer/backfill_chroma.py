"""
backfill_chroma.py
------------------
One-time script to index all facts already in SQLite into ChromaDB.

Run this if you processed PDFs before ChromaDB was wired up:

    python backfill_chroma.py

Progress is logged to stdout. Safe to re-run (upsert is idempotent).
"""

import logging
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 200


def main():
    from app.database import SessionLocal
    from app.models import Fact, Document
    from app.vector_store import get_vector_store

    db = SessionLocal()
    vs = get_vector_store()

    total_facts = db.query(Fact).count()
    logger.info(f"Total facts in SQLite: {total_facts}")
    logger.info(f"Facts already in Chroma: {vs.count()}")

    if total_facts == 0:
        logger.info("No facts to backfill. Upload and process PDFs first.")
        return

    offset = 0
    indexed = 0

    while True:
        batch = (
            db.query(Fact)
            .order_by(Fact.document_id, Fact.page_num)
            .offset(offset)
            .limit(BATCH_SIZE)
            .all()
        )
        if not batch:
            break

        # Attach source_dataset from the parent document
        doc_cache: dict = {}
        for fact in batch:
            if fact.document_id not in doc_cache:
                doc = db.query(Document).filter(Document.id == fact.document_id).first()
                doc_cache[fact.document_id] = doc.source_dataset if doc else ""
            fact.source_dataset = doc_cache[fact.document_id]  # type: ignore[attr-defined]

        vs.upsert_facts(batch)
        indexed += len(batch)
        offset += BATCH_SIZE

        pct = indexed / total_facts * 100
        logger.info(f"Indexed {indexed}/{total_facts} ({pct:.1f}%)  —  Chroma total: {vs.count()}")

    db.close()
    logger.info(f"Done. {vs.count()} facts now indexed in ChromaDB.")


if __name__ == "__main__":
    main()

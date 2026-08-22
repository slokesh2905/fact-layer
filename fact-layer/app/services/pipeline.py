import os
import shutil
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models import Document, Fact, ProcessingJob, ProcessingStatus
from app.pdf import PDFParser, Chunker
from app.extraction import FactExtractor, ExtractionContext
from app.extraction.normalizer import normalize_entity, normalize_attribute
import logging

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    def __init__(self):
        self.extractor = FactExtractor()
        self.chunker = Chunker(max_tokens=settings.chunk_max_tokens)

    def process_document(self, document_id: str) -> None:
        asyncio.run(self._process_async(document_id))

    async def _process_async(self, document_id: str) -> None:
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.error(f"Document {document_id} not found")
                return

            self._update_job(db, document_id, "parsing", ProcessingStatus.PARSING, 0.05, "Parsing PDF")
            pages = self._parse_pdf(doc)
            total_pages = len(pages)
            doc.page_count = total_pages
            db.commit()

            self._update_job(db, document_id, "chunking", ProcessingStatus.EXTRACTING, 0.1, "Chunking content")
            chunks = self.chunker.chunk_pages(pages)

            resume_from = doc.last_processed_page or 0
            if resume_from > 0:
                logger.info(f"Resuming {document_id} from page {resume_from}")
                chunks = [c for c in chunks if c.page_num > resume_from]

            self._update_job(
                db, document_id, "extracting", ProcessingStatus.EXTRACTING,
                0.15, f"Extracting facts from {len(chunks)} chunks (page {resume_from + 1}/{total_pages})"
            )

            context = ExtractionContext(
                document_id=doc.id,
                filename=doc.filename,
                source_dataset=doc.source_dataset
            )

            # Split chunks into 10-page windows; each window is processed
            # concurrently via extract_from_chunks() (semaphore-controlled inside).
            page_windows = _group_into_page_windows(chunks, window_size=10)

            for window_idx, window_chunks in enumerate(page_windows):
                if not window_chunks:
                    continue

                # All chunks in the window fire concurrently (bounded by semaphore)
                window_facts = await self.extractor.extract_from_chunks(window_chunks, context)

                self._store_facts(db, doc, window_facts)
                last_page = window_chunks[-1].page_num
                doc.last_processed_page = last_page
                db.commit()

                progress = 0.15 + 0.70 * (last_page / max(total_pages, 1))
                self._update_job(
                    db, document_id, "extracting", ProcessingStatus.EXTRACTING,
                    progress,
                    f"Extracted pages up to {last_page}/{total_pages} "
                    f"({len(window_facts)} facts in window {window_idx + 1}/{len(page_windows)})",
                )
                logger.info(
                    f"[{document_id}] window {window_idx + 1}/{len(page_windows)} — "
                    f"page {last_page}, {len(window_facts)} facts"
                )

            self._update_job(db, document_id, "analyzing", ProcessingStatus.ANALYZING,
                             0.85, "Finding cross-document relationships")
            await self._run_relationship_analysis_async(db, document_id)

            self._update_job(db, document_id, "completed", ProcessingStatus.COMPLETED, 1.0, "Processing complete")
            doc.status = ProcessingStatus.COMPLETED
            doc.processed_at = datetime.utcnow()
            doc.last_processed_page = total_pages
            db.commit()

        except Exception as e:
            logger.error(f"Processing failed for {document_id}: {e}", exc_info=True)
            self._mark_failed(db, document_id, str(e))
        finally:
            db.close()

    def _parse_pdf(self, doc: Document) -> list:
        with PDFParser(doc.file_path) as parser:
            pages = parser.extract_all_pages()
            meta = parser.get_metadata()
            doc.doc_metadata = meta
            return pages

    async def _run_relationship_analysis_async(self, db: Session, document_id: str) -> None:
        """Async-safe relationship analysis — no nested event loops created here."""
        try:
            from app.analysis import detect_relationships_async
            await detect_relationships_async(db, self.extractor, new_document_id=document_id)
        except Exception as e:
            logger.error(f"Relationship analysis failed for {document_id}: {e}")

    def _store_facts(self, db: Session, doc: Document, facts: list) -> None:
        stored: list = []
        for fact_data in facts:
            fact = Fact(
                document_id=doc.id,
                page_num=fact_data.page_num,
                char_start=fact_data.char_start,
                char_end=fact_data.char_end,
                entity=fact_data.entity,
                entity_normalized=normalize_entity(fact_data.entity),
                attribute=fact_data.attribute,
                attribute_normalized=normalize_attribute(fact_data.attribute),
                value=fact_data.value,
                value_numeric=parse_numeric(fact_data.value),
                unit=fact_data.unit,
                fact_type=fact_data.fact_type,
                time_period=fact_data.time_period,
                scope=fact_data.scope,
                qualifier=fact_data.qualifier,
                confidence=fact_data.confidence,
                raw_evidence=fact_data.raw_evidence or fact_data.value,
                context={
                    "source_dataset": doc.source_dataset,
                    "filename": doc.filename,
                    "extra_properties": fact_data.extra_properties or {},
                }
            )
            db.add(fact)
            stored.append(fact)
        db.commit()

        # Index in ChromaDB for semantic search (non-fatal if Chroma unavailable)
        try:
            from app.vector_store import get_vector_store
            # Attach source_dataset so Chroma metadata is filterable
            for f in stored:
                if not hasattr(f, "source_dataset"):
                    f.source_dataset = doc.source_dataset  # type: ignore[attr-defined]
            get_vector_store().upsert_facts(stored)
        except Exception as e:
            logger.warning(f"ChromaDB upsert skipped: {e}")

    def _update_job(self, db: Session, doc_id: str, stage: str, status: ProcessingStatus, progress: float, message: str):
        job = db.query(ProcessingJob).filter(ProcessingJob.document_id == doc_id).first()
        if not job:
            job = ProcessingJob(document_id=doc_id, stage=stage)
            db.add(job)
        job.stage = stage
        job.status = status
        job.progress = progress
        job.message = message
        if status == ProcessingStatus.PARSING and job.started_at is None:
            job.started_at = datetime.utcnow()
        if status in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED):
            job.completed_at = datetime.utcnow()
        db.commit()

    def _mark_failed(self, db: Session, doc_id: str, error: str):
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = ProcessingStatus.FAILED
            doc.error_message = error
        self._update_job(db, doc_id, "failed", ProcessingStatus.FAILED, 0, error)
        db.commit()


def _group_into_page_windows(chunks: list, window_size: int) -> list:
    """
    Split a flat list of Chunks into sub-lists, each covering at most
    `window_size` distinct page numbers.  Chunks on the same page always
    stay together in the same window.
    """
    if not chunks:
        return []

    windows: list = []
    current_window: list = []
    pages_in_window: set = set()

    for chunk in chunks:
        page = chunk.page_num
        if page not in pages_in_window and len(pages_in_window) >= window_size:
            windows.append(current_window)
            current_window = []
            pages_in_window = set()
        current_window.append(chunk)
        pages_in_window.add(page)

    if current_window:
        windows.append(current_window)

    return windows


def parse_numeric(value: str) -> Optional[float]:
    import re
    cleaned = re.sub(r"[^\d\.\-\+]", "", value.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def create_document_record(filename: str, file_path: str, source_dataset: Optional[str] = None) -> str:
    db = SessionLocal()
    try:
        file_size = os.path.getsize(file_path)
        doc = Document(
            filename=filename,
            source_dataset=source_dataset,
            file_path=file_path,
            file_size=file_size,
            status=ProcessingStatus.PENDING,
        )
        db.add(doc)
        db.commit()
        doc_id = doc.id

        job = ProcessingJob(document_id=doc_id, stage="created", status=ProcessingStatus.PENDING)
        db.add(job)
        db.commit()

        return doc_id
    finally:
        db.close()


def save_uploaded_file(upload_file, filename: str, source_dataset: Optional[str] = None) -> str:
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    file_path = settings.upload_path / filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(upload_file, f)

    return str(file_path)

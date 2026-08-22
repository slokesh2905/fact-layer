#!/usr/bin/env python3
"""
Process starter datasets and run cross-document analysis.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import init_db, SessionLocal
from app.models import Document, ProcessingStatus
from app.services import create_document_record, ProcessingPipeline

STARTER_DATASETS = {
    "delhivery": [
        "../starter-datasets/delhivery/01-delhivery-prospectus-2022-excerpt.pdf",
        "../starter-datasets/delhivery/02-delhivery-annual-report-fy24-excerpt.pdf",
        "../starter-datasets/delhivery/03-delhivery-q4-fy24-earnings-presentation.pdf",
    ],
    "india-macroeconomy": [
        "../starter-datasets/india-macroeconomy/01-india-economic-survey-2024-25-excerpt.pdf",
        "../starter-datasets/india-macroeconomy/02-rbi-annual-report-2024-25-excerpt.pdf",
        "../starter-datasets/india-macroeconomy/03-imf-india-2025-article-iv-excerpt.pdf",
    ],
}


def process_dataset(dataset_name: str, pdf_paths: list):
    print(f"\n{'='*60}")
    print(f"Processing dataset: {dataset_name}")
    print(f"{'='*60}")

    pipeline = ProcessingPipeline()

    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            print(f"  [WARN] File not found: {pdf_path}")
            continue

        filename = os.path.basename(pdf_path)
        print(f"  [INFO] Processing: {filename}")

        doc_id = create_document_record(filename, pdf_path, dataset_name)
        print(f"     Document ID: {doc_id}")

        pipeline.process_document(doc_id)

        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc.status == ProcessingStatus.COMPLETED:
                print(f"     [OK] Completed - {doc.page_count} pages")
            else:
                print(f"     [FAIL] Failed: {doc.error_message}")
        finally:
            db.close()


def main():
    print("Initializing database...")
    init_db()
    print("Database ready.")

    for dataset_name, pdf_paths in STARTER_DATASETS.items():
        process_dataset(dataset_name, pdf_paths)

    print("\n" + "="*60)
    print("Running cross-document relationship analysis...")
    print("="*60)

    from app.analysis import detect_relationships
    from app.extraction import FactExtractor

    db = SessionLocal()
    try:
        extractor = FactExtractor()
        relationships = detect_relationships(db, extractor)
        print(f"\n[OK] Analysis complete! Found {len(relationships)} relationships.")

        from app.models import RelationshipType
        by_type = {}
        for rel in relationships:
            by_type[rel.relationship_type.value] = by_type.get(rel.relationship_type.value, 0) + 1

        for rel_type, count in by_type.items():
            print(f"  {rel_type}: {count}")

    finally:
        db.close()

    print("\n[DONE] All done! Start the API with: uvicorn app.main:app --reload")
    print("Then open the UI with: streamlit run ui/streamlit_app.py")


if __name__ == "__main__":
    main()
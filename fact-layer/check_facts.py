from app.database import SessionLocal
from app.models import Fact, Document
from sqlalchemy import func
db = SessionLocal()

# Check facts per document
facts_per_doc = db.query(Fact.document_id, func.count(Fact.id)).group_by(Fact.document_id).all()
for doc_id, count in facts_per_doc:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    print(f'{doc_id} ({doc.filename if doc else "NO DOC"}): {count} facts')

db.close()
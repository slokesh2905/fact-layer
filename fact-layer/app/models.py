import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime, ForeignKey, Enum, Index, JSON
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship, declared_attr
from app.database import Base


class FactType(str, enum.Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"
    PERCENTAGE = "percentage"
    RATIO = "ratio"


class RelationshipType(str, enum.Enum):
    CORROBORATES = "corroborates"
    CONTRADICTS = "contradicts"
    RECONCILES = "reconciles"
    UNRELATED = "unrelated"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    source_dataset = Column(String(100), nullable=True)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    doc_metadata = Column(SQLiteJSON, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    last_processed_page = Column(Integer, default=0, nullable=False, server_default="0")

    facts = relationship("Fact", back_populates="document", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_source_dataset", "source_dataset"),
        Index("ix_documents_status", "status"),
    )


class Fact(Base):
    __tablename__ = "facts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_num = Column(Integer, nullable=False)
    char_start = Column(Integer, nullable=False)
    char_end = Column(Integer, nullable=False)

    entity = Column(String(255), nullable=False)
    entity_normalized = Column(String(255), nullable=True, index=True)
    attribute = Column(String(255), nullable=False)
    attribute_normalized = Column(String(255), nullable=True, index=True)
    value = Column(Text, nullable=False)
    value_numeric = Column(Float, nullable=True)
    unit = Column(String(100), nullable=True)
    fact_type = Column(Enum(FactType), nullable=False)

    time_period = Column(String(100), nullable=True)
    time_period_start = Column(DateTime, nullable=True)
    time_period_end = Column(DateTime, nullable=True)
    scope = Column(String(255), nullable=True)
    qualifier = Column(Text, nullable=True)

    confidence = Column(Float, default=0.0, nullable=False)
    raw_evidence = Column(Text, nullable=False)
    context = Column(SQLiteJSON, nullable=True)

    document = relationship("Document", back_populates="facts")
    relationships_a = relationship("FactRelationship", foreign_keys="FactRelationship.fact_id_a", back_populates="fact_a")
    relationships_b = relationship("FactRelationship", foreign_keys="FactRelationship.fact_id_b", back_populates="fact_b")

    __table_args__ = (
        Index("ix_facts_entity_attr_period", "entity_normalized", "attribute_normalized", "time_period"),
        Index("ix_facts_document", "document_id"),
    )


class FactRelationship(Base):
    __tablename__ = "fact_relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fact_id_a = Column(String(36), ForeignKey("facts.id", ondelete="CASCADE"), nullable=False)
    fact_id_b = Column(String(36), ForeignKey("facts.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(Enum(RelationshipType), nullable=False)
    explanation = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    triggered_by_document_id = Column(String(36), nullable=True)

    fact_a = relationship("Fact", foreign_keys=[fact_id_a], back_populates="relationships_a")
    fact_b = relationship("Fact", foreign_keys=[fact_id_b], back_populates="relationships_b")

    __table_args__ = (
        Index("ix_relationships_fact_a", "fact_id_a"),
        Index("ix_relationships_fact_b", "fact_id_b"),
        Index("ix_relationships_type", "relationship_type"),
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(50), nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    document = relationship("Document", back_populates="processing_jobs")

    __table_args__ = (
        Index("ix_jobs_document", "document_id"),
    )
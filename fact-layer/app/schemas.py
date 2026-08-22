from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class FactType(str, Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"
    PERCENTAGE = "percentage"
    RATIO = "ratio"


class RelationshipType(str, Enum):
    CORROBORATES = "corroborates"
    CONTRADICTS = "contradicts"
    RECONCILES = "reconciles"
    UNRELATED = "unrelated"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: ProcessingStatus
    message: str


class DocumentStatusResponse(BaseModel):
    document_id: str
    filename: str
    status: ProcessingStatus
    source_dataset: Optional[str] = None
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None


class EvidenceSpan(BaseModel):
    char_start: int
    char_end: int
    text: str


class FactResponse(BaseModel):
    id: str
    document_id: str
    page_num: int
    entity: str
    entity_normalized: Optional[str] = None
    attribute: str
    attribute_normalized: Optional[str] = None
    value: str
    value_numeric: Optional[float] = None
    unit: Optional[str] = None
    fact_type: FactType
    time_period: Optional[str] = None
    scope: Optional[str] = None
    qualifier: Optional[str] = None
    confidence: float
    evidence: EvidenceSpan
    context: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class FactDetailResponse(FactResponse):
    raw_evidence: str
    document_filename: str


class FactRelationshipResponse(BaseModel):
    id: str
    fact_id_a: str
    fact_id_b: str
    relationship_type: RelationshipType
    explanation: str
    confidence: float
    detected_at: datetime

    class Config:
        from_attributes = True


class EntityTimelineResponse(BaseModel):
    entity: str
    facts: List[FactResponse]


class RelationshipsFilter(BaseModel):
    relationship_type: Optional[RelationshipType] = None
    entity: Optional[str] = None
    attribute: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    entity: Optional[str] = None
    attribute: Optional[str] = None


class SearchResult(BaseModel):
    fact: FactResponse
    score: float


class ProcessingJobResponse(BaseModel):
    id: str
    document_id: str
    stage: str
    status: ProcessingStatus
    progress: float
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_documents: int
    total_facts: int
    total_relationships: int
    facts_by_type: Dict[str, int]
    relationships_by_type: Dict[str, int]
    entities_count: int
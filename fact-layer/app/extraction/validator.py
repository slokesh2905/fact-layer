import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
from app.extraction.normalizer import normalize_entity, normalize_attribute, normalize_unit, parse_numeric_value


class ExtractedFact(BaseModel):
    entity: str
    attribute: str
    value: str
    unit: Optional[str] = None
    time_period: str
    scope: Optional[str] = None
    qualifier: Optional[str] = None
    fact_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_span: Dict[str, int]
    extra_properties: Optional[Dict[str, Any]] = Field(default_factory=dict)
    # Enriched fields added during extraction
    document_id: Optional[str] = None
    page_num: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    source_dataset: Optional[str] = None
    raw_evidence: Optional[str] = None

    @field_validator("fact_type")
    @classmethod
    def validate_fact_type(cls, v):
        valid = ["numeric", "percentage", "categorical", "temporal", "ratio"]
        if v not in valid:
            raise ValueError(f"fact_type must be one of {valid}")
        return v

    @field_validator("evidence_span")
    @classmethod
    def validate_evidence_span(cls, v):
        if not isinstance(v, dict):
            raise ValueError("evidence_span must be a dict")
        if "start" not in v or "end" not in v:
            raise ValueError("evidence_span must have start and end")
        if v["start"] < 0 or v["end"] < v["start"]:
            raise ValueError("invalid evidence_span indices")
        return v


class ExtractionResult(BaseModel):
    facts: List[ExtractedFact]


def validate_extraction_output(raw_output: str) -> Tuple[Optional[ExtractionResult], List[str]]:
    errors = []
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return None, errors

    if not isinstance(data, dict) or "facts" not in data:
        errors.append("Output must be a dict with 'facts' array")
        return None, errors

    if not isinstance(data["facts"], list):
        errors.append("'facts' must be an array")
        return None, errors

    validated_facts = []
    for i, fact in enumerate(data["facts"]):
        try:
            validated_facts.append(ExtractedFact(**fact))
        except Exception as e:
            errors.append(f"Fact {i}: {e}")

    if validated_facts:
        return ExtractionResult(facts=validated_facts), errors
    return None, errors


def verify_evidence_span(fact: ExtractedFact, chunk_text: str) -> Tuple[bool, str]:
    start = fact.evidence_span["start"]
    end = fact.evidence_span["end"]

    if start >= len(chunk_text) or end > len(chunk_text):
        return False, f"Evidence span [{start}:{end}] exceeds chunk length {len(chunk_text)}"

    evidence_text = chunk_text[start:end].strip()
    if not evidence_text:
        return False, "Evidence span is empty"

    value_lower = fact.value.lower()
    evidence_lower = evidence_text.lower()

    if fact.fact_type in ("numeric", "percentage"):
        fact_num = parse_numeric_value(fact.value)
        if fact_num is not None:
            evidence_nums = re.findall(r"[\d,]+\.?\d*", evidence_text)
            found = False
            for num_str in evidence_nums:
                try:
                    if abs(float(num_str.replace(",", "")) - fact_num) < 0.01:
                        found = True
                        break
                except ValueError:
                    continue
            if not found:
                return False, f"Numeric value {fact.value} not found in evidence: '{evidence_text[:100]}'"

    return True, "OK"


def validate_fact_against_chunk(fact: ExtractedFact, chunk_text: str) -> Tuple[bool, List[str]]:
    errors = []

    ok, msg = verify_evidence_span(fact, chunk_text)
    if not ok:
        errors.append(msg)

    if fact.confidence < 0.0 or fact.confidence > 1.0:
        errors.append(f"Confidence {fact.confidence} out of range [0,1]")

    if fact.fact_type in ("numeric", "percentage") and parse_numeric_value(fact.value) is None:
        errors.append(f"Non-numeric value for {fact.fact_type} fact: {fact.value}")

    if fact.unit:
        norm_unit = normalize_unit(fact.unit)
        if not norm_unit:
            errors.append(f"Unrecognized unit: {fact.unit}")

    return len(errors) == 0, errors


def filter_and_score_facts(facts: List[ExtractedFact], chunk_text: str, min_confidence: float = 0.5) -> List[ExtractedFact]:
    valid_facts = []
    for fact in facts:
        valid, errors = validate_fact_against_chunk(fact, chunk_text)
        if valid and fact.confidence >= min_confidence:
            fact.entity = normalize_entity(fact.entity)
            fact.attribute = normalize_attribute(fact.attribute)
            fact.unit = normalize_unit(fact.unit)
            valid_facts.append(fact)
    return valid_facts
import re
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models import Fact, FactRelationship, RelationshipType
from app.extraction.normalizer import normalize_entity, normalize_attribute, similarity
from app.extraction.extractor import FactExtractor
import logging

logger = logging.getLogger(__name__)


class EntityResolver:
    def __init__(self, db: Session):
        self.db = db
        self._entity_cache: Dict[str, str] = {}
        self._attribute_cache: Dict[str, str] = {}

    def get_all_entities(self) -> List[str]:
        entities = self.db.query(Fact.entity_normalized).distinct().all()
        return [e[0] for e in entities if e[0]]

    def get_all_attributes(self) -> List[str]:
        attrs = self.db.query(Fact.attribute_normalized).distinct().all()
        return [a[0] for a in attrs if a[0]]

    def resolve_entity(self, entity: str) -> str:
        if entity in self._entity_cache:
            return self._entity_cache[entity]
        normalized = normalize_entity(entity)
        known_entities = self.get_all_entities()
        match = self._find_best_match(normalized, known_entities, threshold=0.85)
        result = match if match else normalized
        self._entity_cache[entity] = result
        return result

    def resolve_attribute(self, attribute: str) -> str:
        if attribute in self._attribute_cache:
            return self._attribute_cache[attribute]
        normalized = normalize_attribute(attribute)
        known_attrs = self.get_all_attributes()
        match = self._find_best_match(normalized, known_attrs, threshold=0.8)
        result = match if match else normalized
        self._attribute_cache[attribute] = result
        return result

    def _find_best_match(self, value: str, candidates: List[str], threshold: float) -> Optional[str]:
        best = None
        best_score = 0.0
        for cand in candidates:
            score = similarity(value, cand)
            if score > best_score and score >= threshold:
                best_score = score
                best = cand
        return best


class FactComparator:
    NUMERIC_TOLERANCE = 0.05

    def __init__(self, extractor: FactExtractor):
        self.extractor = extractor

    def should_compare(self, fact_a: Fact, fact_b: Fact) -> bool:
        if fact_a.id == fact_b.id:
            return False
        # Cross-document only
        if fact_a.document_id == fact_b.document_id:
            return False
        if fact_a.entity_normalized != fact_b.entity_normalized:
            return False
        if fact_a.attribute_normalized != fact_b.attribute_normalized:
            return False
        if not _periods_overlap(fact_a.time_period, fact_b.time_period):
            return False
        return True

    def compare_numeric(self, fact_a: Fact, fact_b: Fact) -> Dict[str, Any]:
        val_a = fact_a.value_numeric
        val_b = fact_b.value_numeric
        if val_a is None or val_b is None:
            return {"comparable": False, "diff_pct": None}
        if val_a == 0 and val_b == 0:
            return {"comparable": True, "diff_pct": 0.0, "same": True}
        if val_a == 0 or val_b == 0:
            return {"comparable": True, "diff_pct": 1.0, "same": False}
        diff_pct = abs(val_a - val_b) / max(abs(val_a), abs(val_b))
        return {"comparable": True, "diff_pct": diff_pct, "same": diff_pct <= self.NUMERIC_TOLERANCE}

    def compare_categorical(self, fact_a: Fact, fact_b: Fact) -> Dict[str, Any]:
        same = fact_a.value.strip().lower() == fact_b.value.strip().lower()
        return {"comparable": True, "same": same}

    def compare_facts(self, fact_a: Fact, fact_b: Fact) -> Dict[str, Any]:
        if fact_a.fact_type != fact_b.fact_type:
            return {"comparable": False, "reason": "Different fact types"}
        if fact_a.fact_type.value in ("numeric", "percentage", "ratio"):
            return self.compare_numeric(fact_a, fact_b)
        return self.compare_categorical(fact_a, fact_b)


def _extract_year(period: str) -> str:
    """Normalize a time period string to a comparable year token."""
    m = re.search(r'20\d{2}', period)
    if m:
        return m.group(0)
    # Handle FY23, FY24 shorthand
    m2 = re.search(r'FY(\d{2})\b', period, re.IGNORECASE)
    if m2:
        return "20" + m2.group(1)
    return period.lower().strip()


def _periods_overlap(period_a: Optional[str], period_b: Optional[str]) -> bool:
    """Return True if the two period strings refer to the same year."""
    if not period_a or not period_b:
        return True
    # Exact match first
    if period_a == period_b:
        return True
    return _extract_year(period_a) == _extract_year(period_b)


class RelationshipDetector:
    def __init__(self, db: Session, extractor: FactExtractor, new_document_id: Optional[str] = None):
        self.db = db
        self.extractor = extractor
        self.comparator = FactComparator(extractor)
        self.resolver = EntityResolver(db)
        self.new_document_id = new_document_id

    async def find_relationships(self) -> List[FactRelationship]:
        if self.new_document_id:
            return await self._find_incremental()
        return await self._find_full()

    async def _find_incremental(self) -> List[FactRelationship]:
        """Compare only the new document's facts against all existing facts."""
        new_facts = self.db.query(Fact).filter(
            Fact.document_id == self.new_document_id
        ).all()
        existing_facts = self.db.query(Fact).filter(
            Fact.document_id != self.new_document_id
        ).all()

        logger.info(
            f"Incremental: comparing {len(new_facts)} new facts "
            f"against {len(existing_facts)} existing facts"
        )

        # Build a lookup by group key for existing facts
        existing_by_key: Dict[str, List[Fact]] = defaultdict(list)
        for f in existing_facts:
            key = f"{f.entity_normalized}|{f.attribute_normalized}"
            existing_by_key[key].append(f)

        relationships = []
        for new_fact in new_facts:
            key = f"{new_fact.entity_normalized}|{new_fact.attribute_normalized}"
            candidates = existing_by_key.get(key, [])
            for existing_fact in candidates:
                if self.comparator.should_compare(new_fact, existing_fact):
                    rel = await self._detect_relationship(new_fact, existing_fact)
                    if rel:
                        rel.triggered_by_document_id = self.new_document_id
                        relationships.append(rel)

        logger.info(f"Incremental found {len(relationships)} new relationships")
        return relationships

    async def _find_full(self) -> List[FactRelationship]:
        """Full reanalysis — load all facts grouped by entity+attribute."""
        groups = self.db.query(
            Fact.entity_normalized,
            Fact.attribute_normalized,
        ).distinct().all()

        relationships = []
        for entity, attribute in groups:
            group_facts = self.db.query(Fact).filter(
                Fact.entity_normalized == entity,
                Fact.attribute_normalized == attribute,
            ).all()

            if len(group_facts) < 2:
                continue

            for i, fact_a in enumerate(group_facts):
                for fact_b in group_facts[i + 1:]:
                    if self.comparator.should_compare(fact_a, fact_b):
                        rel = await self._detect_relationship(fact_a, fact_b)
                        if rel:
                            relationships.append(rel)

        logger.info(f"Full analysis found {len(relationships)} relationships")
        return relationships

    async def _detect_relationship(self, fact_a: Fact, fact_b: Fact) -> Optional[FactRelationship]:
        comparison = self.comparator.compare_facts(fact_a, fact_b)
        if not comparison.get("comparable", False):
            return None

        if comparison.get("same", False):
            rel_type = RelationshipType.CORROBORATES
            explanation = f"Values agree: {fact_a.value} {fact_a.unit or ''} ≈ {fact_b.value} {fact_b.unit or ''}"
            confidence = 0.9
        else:
            asyncio_result = await self._reconcile_async(fact_a, fact_b)
            if asyncio_result:
                try:
                    rel_type = RelationshipType(asyncio_result["relationship"])
                except ValueError:
                    rel_type = RelationshipType.CONTRADICTS
                explanation = asyncio_result.get("explanation", "")
                confidence = asyncio_result.get("confidence", 0.8)
            else:
                diff = comparison.get("diff_pct", 1.0) or 1.0
                rel_type = RelationshipType.CONTRADICTS
                explanation = (
                    f"Values differ: {fact_a.value} {fact_a.unit or ''} vs "
                    f"{fact_b.value} {fact_b.unit or ''} ({diff * 100:.1f}% difference)"
                )
                confidence = 0.8

        return FactRelationship(
            fact_id_a=fact_a.id,
            fact_id_b=fact_b.id,
            relationship_type=rel_type,
            explanation=explanation,
            confidence=confidence,
        )

    async def _reconcile_async(self, fact_a: Fact, fact_b: Fact) -> Optional[Dict]:
        """Await the LLM reconciliation directly — no nested event loop needed."""
        try:
            return await self.extractor.reconcile_facts(
                self._fact_to_dict(fact_a),
                self._fact_to_dict(fact_b),
            )
        except Exception as e:
            logger.error(f"Reconcile failed: {e}")
            return None

    def _fact_to_dict(self, fact: Fact) -> Dict[str, Any]:
        return {
            "source_dataset": fact.document.source_dataset if fact.document else "Unknown",
            "entity": fact.entity,
            "attribute": fact.attribute,
            "value": fact.value,
            "unit": fact.unit,
            "time_period": fact.time_period,
            "scope": fact.scope,
            "qualifier": fact.qualifier,
            "raw_evidence": fact.raw_evidence,
        }


def detect_relationships(
    db: Session,
    extractor: FactExtractor,
    new_document_id: Optional[str] = None,
) -> List[FactRelationship]:
    """Sync wrapper — used by the manual /analyze/relationships API route."""
    import asyncio
    return asyncio.run(
        detect_relationships_async(db, extractor, new_document_id=new_document_id)
    )


async def detect_relationships_async(
    db: Session,
    extractor: FactExtractor,
    new_document_id: Optional[str] = None,
) -> List[FactRelationship]:
    """
    Async entry point — called from the pipeline which already runs inside
    an event loop (asyncio.run in process_document).
    Incremental mode: only re-evaluates relationships touching the new document.
    Full mode: rebuilds all relationships from scratch.
    """
    if new_document_id:
        # Incremental: only delete relationships involving the new document
        new_fact_ids = db.query(Fact.id).filter(
            Fact.document_id == new_document_id
        ).subquery()
        db.query(FactRelationship).filter(
            (FactRelationship.fact_id_a.in_(new_fact_ids)) |
            (FactRelationship.fact_id_b.in_(new_fact_ids))
        ).delete(synchronize_session="fetch")
    else:
        # Full reanalysis
        db.query(FactRelationship).delete()
    db.commit()

    detector = RelationshipDetector(db, extractor, new_document_id=new_document_id)
    relationships = await detector.find_relationships()

    for rel in relationships:
        db.add(rel)
    db.commit()

    return relationships

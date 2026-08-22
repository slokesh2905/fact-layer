import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher


ENTITY_ALIASES = {
    "delhivery": [
        "delhivery limited", "delhivery ltd", "delhivery pvt ltd", "delhivery private limited",
        "delhivery", "the company", "our company"
    ],
    "india": [
        "india", "the indian economy", "indian economy", "domestic economy"
    ],
    "rbi": [
        "reserve bank of india", "rbi", "the reserve bank", "central bank"
    ],
    "imf": [
        "international monetary fund", "imf", "the fund"
    ],
    "government of india": [
        "government of india", "goi", "central government", "union government"
    ]
}

ATTRIBUTE_SYNONYMS = {
    "revenue": [
        "revenue", "total revenue", "total income", "net sales", "sales", "turnover",
        "income from operations", "operating revenue", "gross revenue"
    ],
    "ebitda": [
        "ebitda", "earnings before interest tax depreciation amortization",
        "operating profit before depreciation", "ebitda profit"
    ],
    "ebitda_margin": [
        "ebitda margin", "ebitda %", "ebitda percentage", "ebitda as percentage of revenue"
    ],
    "profit_after_tax": [
        "profit after tax", "pat", "net profit", "net income", "profit for the year",
        "net earnings"
    ],
    "operating_cash_flow": [
        "operating cash flow", "cash from operations", "net cash from operating activities",
        "cash generated from operations"
    ],
    "total_employees": [
        "total employees", "employee count", "headcount", "workforce", "number of employees",
        "staff strength"
    ],
    "delivery_personnel": [
        "delivery personnel", "delivery staff", "delivery executives", "field staff"
    ],
    "corporate_staff": [
        "corporate staff", "corporate employees", "office staff", "management staff"
    ],
    "gdp_growth": [
        "gdp growth", "real gdp growth", "gross domestic product growth",
        "economic growth rate", "real gdp growth rate"
    ],
    "cpi_inflation": [
        "cpi inflation", "consumer price index inflation", "retail inflation",
        "cpi", "headline inflation"
    ],
    "wpi_inflation": [
        "wpi inflation", "wholesale price index inflation", "wholesale inflation"
    ],
    "fiscal_deficit": [
        "fiscal deficit", "budget deficit", "central government fiscal deficit"
    ],
    "current_account_deficit": [
        "current account deficit", "cad", "current account balance"
    ],
    "segment_revenue": [
        "segment revenue", "revenue by segment", "segment-wise revenue"
    ],
    "cities_covered": [
        "cities covered", "cities served", "number of cities", "city coverage"
    ],
    "pin_codes_covered": [
        "pin codes covered", "pincodes served", "pin code coverage", "postal codes covered"
    ],
    "gateways": [
        "gateways", "sorting centers", "fulfillment centers", "hub count"
    ],
    "vehicles": [
        "vehicles", "fleet size", "number of vehicles", "fleet strength"
    ],
    "ceo": [
        "ceo", "chief executive officer", "managing director", "md & ceo"
    ],
    "acquisition": [
        "acquisition", "acquired", "purchase of", "takeover"
    ],
    "rbi_tolerance_band": [
        "rbi tolerance band", "inflation targeting band", "rbi inflation band"
    ]
}

UNIT_NORMALIZATION = {
    "inr_million": ["rs. million", "rs million", "inr million", "₹ million", "rupees million"],
    "inr_crore": ["rs. crore", "rs crore", "inr crore", "₹ crore", "rupees crore", "cr"],
    "usd_million": ["usd million", "$ million", "us$ million", "dollars million"],
    "percent": ["%", "percent", "per cent", "percentage", "pct"],
    "count": ["count", "number", "nos", "nos.", "units"],
    "ratio": ["ratio", "times", "x", "multiple"],
}


def normalize_entity(entity: str) -> str:
    entity_lower = entity.lower().strip()
    for canonical, aliases in ENTITY_ALIASES.items():
        for alias in aliases:
            if alias in entity_lower or entity_lower in alias:
                return canonical.title()
    return entity.strip().title()


def normalize_attribute(attribute: str) -> str:
    attr_lower = attribute.lower().strip()
    for canonical, synonyms in ATTRIBUTE_SYNONYMS.items():
        for syn in synonyms:
            if syn in attr_lower or attr_lower in syn:
                return canonical
    return attr_lower.replace(" ", "_")


def normalize_unit(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    unit_lower = unit.lower().strip()
    for canonical, variants in UNIT_NORMALIZATION.items():
        for var in variants:
            if var in unit_lower or unit_lower in var:
                return canonical
    return unit_lower


def parse_numeric_value(value: str) -> Optional[float]:
    if not value:
        return None
    cleaned = re.sub(r"[^\d\.\-\+]", "", value.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_time_period(period: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    period = period.strip()
    return period, None, None


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_best_entity_match(entity: str, known_entities: List[str], threshold: float = 0.8) -> Optional[str]:
    best_match = None
    best_score = 0.0
    for known in known_entities:
        score = similarity(entity, known)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = known
    return best_match


def find_best_attribute_match(attribute: str, known_attributes: List[str], threshold: float = 0.8) -> Optional[str]:
    best_match = None
    best_score = 0.0
    for known in known_attributes:
        score = similarity(attribute, known)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = known
    return best_match
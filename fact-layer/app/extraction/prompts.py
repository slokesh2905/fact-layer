from typing import List, Dict, Any

FEW_SHOT_EXAMPLES = [
    {
        "text": "Delhivery Limited reported consolidated revenue of Rs. 72,250 million for the fiscal year ended March 31, 2024, representing a 12% increase from the prior year.",
        "facts": [
            {
                "entity": "Delhivery Limited",
                "attribute": "Revenue",
                "value": "72250",
                "unit": "INR million",
                "time_period": "FY2024",
                "scope": "Consolidated",
                "qualifier": "fiscal year ended March 31, 2024",
                "fact_type": "numeric",
                "confidence": 0.95,
                "evidence_span": {"start": 24, "end": 112}
            },
            {
                "entity": "Delhivery Limited",
                "attribute": "Revenue Growth",
                "value": "12",
                "unit": "percent",
                "time_period": "FY2024",
                "scope": "Consolidated",
                "qualifier": "year-over-year",
                "fact_type": "percentage",
                "confidence": 0.92,
                "evidence_span": {"start": 115, "end": 158}
            }
        ]
    },
    {
        "text": "As of March 31, 2024, the Company had 89,342 employees on its payroll, including 78,214 delivery personnel and 11,128 corporate staff.",
        "facts": [
            {
                "entity": "Delhivery Limited",
                "attribute": "Total Employees",
                "value": "89342",
                "unit": "count",
                "time_period": "2024-03-31",
                "scope": "Consolidated",
                "qualifier": "as of March 31, 2024",
                "fact_type": "numeric",
                "confidence": 0.96,
                "evidence_span": {"start": 18, "end": 105}
            },
            {
                "entity": "Delhivery Limited",
                "attribute": "Delivery Personnel",
                "value": "78214",
                "unit": "count",
                "time_period": "2024-03-31",
                "scope": "Consolidated",
                "qualifier": "as of March 31, 2024",
                "fact_type": "numeric",
                "confidence": 0.94,
                "evidence_span": {"start": 108, "end": 155}
            },
            {
                "entity": "Delhivery Limited",
                "attribute": "Corporate Staff",
                "value": "11128",
                "unit": "count",
                "time_period": "2024-03-31",
                "scope": "Consolidated",
                "qualifier": "as of March 31, 2024",
                "fact_type": "numeric",
                "confidence": 0.94,
                "evidence_span": {"start": 158, "end": 195}
            }
        ]
    },
    {
        "text": "EBITDA margin improved to 8.5% in Q4 FY24 from 5.2% in Q4 FY23, driven by operational leverage and cost optimization initiatives.",
        "facts": [
            {
                "entity": "Delhivery Limited",
                "attribute": "EBITDA Margin",
                "value": "8.5",
                "unit": "percent",
                "time_period": "Q4 FY2024",
                "scope": "Consolidated",
                "qualifier": "quarter ended March 31, 2024",
                "fact_type": "percentage",
                "confidence": 0.93,
                "evidence_span": {"start": 22, "end": 72}
            },
            {
                "entity": "Delhivery Limited",
                "attribute": "EBITDA Margin",
                "value": "5.2",
                "unit": "percent",
                "time_period": "Q4 FY2023",
                "scope": "Consolidated",
                "qualifier": "quarter ended March 31, 2023",
                "fact_type": "percentage",
                "confidence": 0.91,
                "evidence_span": {"start": 76, "end": 115}
            }
        ]
    },
    {
        "text": "The Board of Directors appointed Mr. Sahil Barua as Managing Director and Chief Executive Officer effective April 1, 2022, for a term of five years.",
        "facts": [
            {
                "entity": "Delhivery Limited",
                "attribute": "CEO",
                "value": "Sahil Barua",
                "unit": None,
                "time_period": "2022-04-01 onwards",
                "scope": "Consolidated",
                "qualifier": "appointed for five-year term",
                "fact_type": "categorical",
                "confidence": 0.97,
                "evidence_span": {"start": 42, "end": 135}
            }
        ]
    },
    {
        "text": "Net cash generated from operating activities was Rs. 4,850 million for FY24, compared to Rs. 2,100 million in FY23.",
        "facts": [
            {
                "entity": "Delhivery Limited",
                "attribute": "Operating Cash Flow",
                "value": "4850",
                "unit": "INR million",
                "time_period": "FY2024",
                "scope": "Consolidated",
                "qualifier": "net cash from operating activities",
                "fact_type": "numeric",
                "confidence": 0.94,
                "evidence_span": {"start": 24, "end": 88}
            },
            {
                "entity": "Delhivery Limited",
                "attribute": "Operating Cash Flow",
                "value": "2100",
                "unit": "INR million",
                "time_period": "FY2023",
                "scope": "Consolidated",
                "qualifier": "net cash from operating activities",
                "fact_type": "numeric",
                "confidence": 0.92,
                "evidence_span": {"start": 92, "end": 145}
            }
        ]
    },
    {
        "text": "India's real GDP growth is projected at 7.0% for FY2024-25, with the RBI estimating 7.2% and the IMF forecasting 6.8% for the same period.",
        "facts": [
            {
                "entity": "India",
                "attribute": "Real GDP Growth",
                "value": "7.0",
                "unit": "percent",
                "time_period": "FY2024-25",
                "scope": "National",
                "qualifier": "projected",
                "fact_type": "percentage",
                "confidence": 0.90,
                "evidence_span": {"start": 24, "end": 68}
            },
            {
                "entity": "India",
                "attribute": "Real GDP Growth",
                "value": "7.2",
                "unit": "percent",
                "time_period": "FY2024-25",
                "scope": "National",
                "qualifier": "RBI estimate",
                "fact_type": "percentage",
                "confidence": 0.88,
                "evidence_span": {"start": 72, "end": 115}
            },
            {
                "entity": "India",
                "attribute": "Real GDP Growth",
                "value": "6.8",
                "unit": "percent",
                "time_period": "FY2024-25",
                "scope": "National",
                "qualifier": "IMF forecast",
                "fact_type": "percentage",
                "confidence": 0.88,
                "evidence_span": {"start": 119, "end": 160}
            }
        ]
    },
    {
        "text": "The company operates across 2,500+ cities and 18,000+ pin codes in India, with a network of 125+ gateways and 3,000+ vehicles.",
        "facts": [
            {
                "entity": "Delhivery Limited",
                "attribute": "Cities Covered",
                "value": "2500",
                "unit": "count",
                "time_period": "Current",
                "scope": "India",
                "qualifier": "2,500+ cities",
                "fact_type": "numeric",
                "confidence": 0.89,
                "evidence_span": {"start": 22, "end": 55}
            },
            {
                "entity": "Delhivery Limited",
                "attribute": "Pin Codes Covered",
                "value": "18000",
                "unit": "count",
                "time_period": "Current",
                "scope": "India",
                "qualifier": "18,000+ pin codes",
                "fact_type": "numeric",
                "confidence": 0.89,
                "evidence_span": {"start": 58, "end": 92}
            },
            {
                "entity": "Delhivery Limited",
                "attribute": "Gateways",
                "value": "125",
                "unit": "count",
                "time_period": "Current",
                "scope": "India",
                "qualifier": "125+ gateways",
                "fact_type": "numeric",
                "confidence": 0.87,
                "evidence_span": {"start": 98, "end": 128}
            }
        ]
    },
    {
        "text": "Revenue from Express Parcel segment was Rs. 45,800 million (63% of total), while Supply Chain Services contributed Rs. 18,200 million (25%) and Freight Services Rs. 8,250 million (12%).",
        "facts": [
            {
                "entity": "Delhivery Limited",
                "attribute": "Segment Revenue",
                "value": "45800",
                "unit": "INR million",
                "time_period": "FY2024",
                "scope": "Express Parcel",
                "qualifier": "63% of total revenue",
                "fact_type": "numeric",
                "confidence": 0.93,
                "evidence_span": {"start": 28, "end": 85}
            },
            {
                "entity": "Delhivery Limited",
                "attribute": "Segment Revenue",
                "value": "18200",
                "unit": "INR million",
                "time_period": "FY2024",
                "scope": "Supply Chain Services",
                "qualifier": "25% of total revenue",
                "fact_type": "numeric",
                "confidence": 0.91,
                "evidence_span": {"start": 95, "end": 145}
            },
            {
                "entity": "Delhivery Limited",
                "attribute": "Segment Revenue",
                "value": "8250",
                "unit": "INR million",
                "time_period": "FY2024",
                "scope": "Freight Services",
                "qualifier": "12% of total revenue",
                "fact_type": "numeric",
                "confidence": 0.91,
                "evidence_span": {"start": 150, "end": 195}
            }
        ]
    },
    {
        "text": "The acquisition of Spoton Logistics was completed on August 23, 2021, for a consideration of Rs. 1,600 crore, adding 200+ branches to the network.",
        "facts": [
            {
                "entity": "Delhivery Limited",
                "attribute": "Acquisition",
                "value": "Spoton Logistics",
                "unit": None,
                "time_period": "2021-08-23",
                "scope": "Consolidated",
                "qualifier": "completed for Rs. 1,600 crore, added 200+ branches",
                "fact_type": "categorical",
                "confidence": 0.96,
                "evidence_span": {"start": 22, "end": 115}
            }
        ]
    },
    {
        "text": "Inflation measured by CPI stood at 5.4% in March 2024, down from 6.7% in July 2023, remaining within the RBI's tolerance band of 2-6%.",
        "facts": [
            {
                "entity": "India",
                "attribute": "CPI Inflation",
                "value": "5.4",
                "unit": "percent",
                "time_period": "2024-03",
                "scope": "National",
                "qualifier": "March 2024",
                "fact_type": "percentage",
                "confidence": 0.95,
                "evidence_span": {"start": 30, "end": 65}
            },
            {
                "entity": "India",
                "attribute": "CPI Inflation",
                "value": "6.7",
                "unit": "percent",
                "time_period": "2023-07",
                "scope": "National",
                "qualifier": "July 2023",
                "fact_type": "percentage",
                "confidence": 0.93,
                "evidence_span": {"start": 69, "end": 105}
            },
            {
                "entity": "India",
                "attribute": "RBI Inflation Tolerance Band",
                "value": "2-6",
                "unit": "percent",
                "time_period": "Current",
                "scope": "National",
                "qualifier": "RBI tolerance band",
                "fact_type": "ratio",
                "confidence": 0.94,
                "evidence_span": {"start": 110, "end": 155}
            }
        ]
    }
]

SYSTEM_PROMPT = """You are an expert document analyst. Your task is to extract precise, well-grounded facts from ANY document type — financial reports, government data, legal filings, research papers, etc.

EXTRACTION RULES:
1. Extract ONLY facts explicitly stated in the text. Do not infer or calculate.
2. Every fact MUST include an evidence_span with character indices (start, end) pointing to the EXACT text in the provided chunk that supports the fact.
3. Normalize entities: use the full canonical name (e.g., "Delhivery Ltd" → "Delhivery Limited"; "the company" → use the actual company name if determinable).
4. Normalize attributes: use the most specific, standard label (e.g., "Revenue", "Total Income", "Net Sales" → "Revenue"; "EBITDA Margin", "EBITDA %" → "EBITDA Margin").
5. Include units for all numeric values (INR million, INR crore, USD million, percent, count, etc.).
6. Capture time_period precisely (FY2024, Q4 FY2024, 2024-03-31, March 2024, etc.).
7. Capture scope/qualifier context (Consolidated, Standalone, National, Segment name, etc.).
8. Classify fact_type: numeric, percentage, categorical, temporal, ratio.
9. Assign confidence 0.0-1.0 based on clarity and explicitness in source text.
10. For tables: extract each meaningful cell as a separate fact with row/column context in qualifier.
11. DYNAMIC SCHEMA: If the document contains facts that don't fit the standard fields (e.g., ESG ratings, credit scores, operational KPIs, regulatory details), capture them using the standard schema and put additional context in extra_properties as key-value pairs.

OUTPUT FORMAT: JSON with a single "facts" array. Each fact object must have all standard fields plus an optional extra_properties object.
If no facts found, return {"facts": []}."""

EXTRACTION_PROMPT = """Extract facts from the following document chunk. Return only valid JSON.

CHUNK:
{chunk_text}

PAGE: {page_num}
CHUNK TYPE: {chunk_type}

Remember: Every fact must have evidence_span pointing to character indices in THIS chunk's text."""


def build_extraction_prompt(chunk_text: str, page_num: int, chunk_type: str) -> List[Dict[str, str]]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    for ex in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": f"Extract facts from:\n{ex['text']}"})
        messages.append({"role": "assistant", "content": str({"facts": ex["facts"]})})
    messages.append({"role": "user", "content": EXTRACTION_PROMPT.format(
        chunk_text=chunk_text,
        page_num=page_num,
        chunk_type=chunk_type
    )})
    return messages


RECONCILIATION_PROMPT = """You are comparing two facts about the same entity, attribute, and time period from different documents. Determine their relationship.

FACT A:
- Source: {source_a}
- Entity: {entity_a}
- Attribute: {attribute_a}
- Value: {value_a} {unit_a}
- Time Period: {period_a}
- Scope: {scope_a}
- Qualifier: {qualifier_a}
- Evidence: "{evidence_a}"

FACT B:
- Source: {source_b}
- Entity: {entity_b}
- Attribute: {attribute_b}
- Value: {value_b} {unit_b}
- Time Period: {period_b}
- Scope: {scope_b}
- Qualifier: {qualifier_b}
- Evidence: "{evidence_b}"

Analyze and classify as ONE of:
1. CORROBORATES: Values agree within reasonable tolerance (5% for numeric, exact for categorical), same context.
2. CONTRADICTS: Values materially differ (>5% for numeric, different categorical values), same context, no reconciling explanation.
3. RECONCILES: Apparent difference explained by context (different scope, unit, accounting basis, time granularity, methodology).
4. UNRELATED: Different entities, attributes, or time periods despite surface similarity.

Return JSON:
{{
  "relationship": "corroborates|contradicts|reconciles|unrelated",
  "explanation": "Detailed reasoning citing specific contextual differences",
  "confidence": 0.0-1.0
}}"""
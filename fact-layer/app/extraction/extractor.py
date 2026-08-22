import asyncio
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging

from app.config import settings
from app.extraction.prompts import build_extraction_prompt, RECONCILIATION_PROMPT
from app.extraction.validator import validate_extraction_output, filter_and_score_facts, ExtractedFact
from app.pdf.chunker import Chunk

logger = logging.getLogger(__name__)


@dataclass
class ExtractionContext:
    document_id: str
    filename: str
    source_dataset: Optional[str] = None


class LLMExtractor(ABC):
    @abstractmethod
    async def extract(self, messages: List[Dict[str, str]]) -> str:
        pass

    @abstractmethod
    async def reconcile(self, fact_a: Dict, fact_b: Dict) -> Dict[str, Any]:
        pass


class NVIDIAExtractor(LLMExtractor):
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
        )
        self.model = settings.nvidia_model
        self.max_tokens = 2000
        self.temperature = 0.1

    async def extract(self, messages: List[Dict[str, str]]) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"

    async def reconcile(self, fact_a: Dict, fact_b: Dict) -> Dict[str, Any]:
        prompt = RECONCILIATION_PROMPT.format(
            source_a=fact_a.get("source_dataset", "Unknown"),
            entity_a=fact_a.get("entity", ""),
            attribute_a=fact_a.get("attribute", ""),
            value_a=fact_a.get("value", ""),
            unit_a=fact_a.get("unit", ""),
            period_a=fact_a.get("time_period", ""),
            scope_a=fact_a.get("scope", ""),
            qualifier_a=fact_a.get("qualifier", ""),
            evidence_a=fact_a.get("raw_evidence", "")[:200],
            source_b=fact_b.get("source_dataset", "Unknown"),
            entity_b=fact_b.get("entity", ""),
            attribute_b=fact_b.get("attribute", ""),
            value_b=fact_b.get("value", ""),
            unit_b=fact_b.get("unit", ""),
            period_b=fact_b.get("time_period", ""),
            scope_b=fact_b.get("scope", ""),
            qualifier_b=fact_b.get("qualifier", ""),
            evidence_b=fact_b.get("raw_evidence", "")[:200],
        )
        messages = [
            {"role": "system", "content": "You are a precise fact comparison engine. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]
        raw = await self.extract(messages)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"relationship": "unrelated", "explanation": "Failed to parse", "confidence": 0.0}


class OllamaExtractor(LLMExtractor):
    def __init__(self, model: str = "llama3.1:70b", base_url: str = "http://localhost:11434/v1"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key="ollama",
            base_url=base_url,
        )
        self.model = model
        self.max_tokens = 2000
        self.temperature = 0.1

    async def extract(self, messages: List[Dict[str, str]]) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"

    async def reconcile(self, fact_a: Dict, fact_b: Dict) -> Dict[str, Any]:
        prompt = RECONCILIATION_PROMPT.format(
            source_a=fact_a.get("source_dataset", "Unknown"),
            entity_a=fact_a.get("entity", ""),
            attribute_a=fact_a.get("attribute", ""),
            value_a=fact_a.get("value", ""),
            unit_a=fact_a.get("unit", ""),
            period_a=fact_a.get("time_period", ""),
            scope_a=fact_a.get("scope", ""),
            qualifier_a=fact_a.get("qualifier", ""),
            evidence_a=fact_a.get("raw_evidence", "")[:200],
            source_b=fact_b.get("source_dataset", "Unknown"),
            entity_b=fact_b.get("entity", ""),
            attribute_b=fact_b.get("attribute", ""),
            value_b=fact_b.get("value", ""),
            unit_b=fact_b.get("unit", ""),
            period_b=fact_b.get("time_period", ""),
            scope_b=fact_b.get("scope", ""),
            qualifier_b=fact_b.get("qualifier", ""),
            evidence_b=fact_b.get("raw_evidence", "")[:200],
        )
        messages = [
            {"role": "system", "content": "You are a precise fact comparison engine. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]
        raw = await self.extract(messages)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"relationship": "unrelated", "explanation": "Failed to parse", "confidence": 0.0}


class MockExtractor(LLMExtractor):
    """Mock extractor for demo/testing without API keys. Does pattern-based extraction from text."""

    def __init__(self):
        self.call_count = 0
        self.document_entity = "Unknown Entity"
        import re
        self.number_pattern = re.compile(r'[\d,]+\.?\d*')
        self.percent_pattern = re.compile(r'([\d,]+\.?\d*)\s*%')
        self.currency_pattern = re.compile(r'(?:Rs\.?|INR|₹)\s*([\d,]+\.?\d*)\s*(million|crore|cr|billion|bn|thousand)')
        self.date_pattern = re.compile(r'(?:FY|Q[1-4]|FY\d{2,4}|20\d{2}[-/]\d{2,4})', re.IGNORECASE)

    def set_document_entity(self, entity: str):
        self.document_entity = entity

    async def extract(self, messages: List[Dict[str, str]]) -> str:
        self.call_count += 1
        # The last user message contains the prompt with chunk text
        # Extract the chunk text from the prompt (after "CHUNK:" marker)
        user_msg = messages[-1].get("content", "") if messages else ""
        
        # Find the chunk text in the prompt - it's after "CHUNK:\n"
        chunk_text = user_msg
        if "CHUNK:\n" in user_msg:
            chunk_text = user_msg.split("CHUNK:\n", 1)[1]
            # Remove the PAGE and CHUNK TYPE lines at the end
            if "\nPAGE:" in chunk_text:
                chunk_text = chunk_text.split("\nPAGE:", 1)[0]
        
        return self._extract_facts_from_text(chunk_text)

    async def reconcile(self, fact_a: Dict, fact_b: Dict) -> Dict[str, Any]:
        val_a = fact_a.get("value", "")
        val_b = fact_b.get("value", "")
        unit_a = fact_a.get("unit", "")
        unit_b = fact_b.get("unit", "")
        scope_a = fact_a.get("scope", "")
        scope_b = fact_b.get("scope", "")

        try:
            num_a = float(val_a.replace(",", ""))
            num_b = float(val_b.replace(",", ""))
            if num_a == 0 and num_b == 0:
                diff = 0
            elif num_a == 0 or num_b == 0:
                diff = 1.0
            else:
                diff = abs(num_a - num_b) / max(abs(num_a), abs(num_b))
        except (ValueError, ZeroDivisionError):
            diff = 1.0 if val_a != val_b else 0

        if diff < 0.05:
            return {"relationship": "corroborates", "explanation": f"Values agree within 5%: {val_a} vs {val_b}", "confidence": 0.9}
        elif scope_a != scope_b and scope_a and scope_b:
            return {"relationship": "reconciles", "explanation": f"Different scopes: {scope_a} vs {scope_b}", "confidence": 0.85}
        elif unit_a != unit_b and unit_a and unit_b:
            return {"relationship": "reconciles", "explanation": f"Different units: {unit_a} vs {unit_b}", "confidence": 0.8}
        else:
            return {"relationship": "contradicts", "explanation": f"Values differ: {val_a} {unit_a} vs {val_b} {unit_b} (diff: {diff*100:.1f}%)", "confidence": 0.8}

    def _extract_facts_from_text(self, text: str) -> str:
        facts = []
        text_lower = text.lower()
        lines = text.split('\n')

        # Use the document entity set by the caller, fall back to text detection
        doc_entity = self.document_entity
        if doc_entity == "Unknown Entity":
            doc_entity = self._identify_document_entity(text_lower)
        section_context = self._identify_section_context(text_lower)

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if len(line_lower) < 5:
                continue

            # Skip separator lines
            if line_lower.count('-') > len(line) * 0.4 or line_lower.count('.') > len(line) * 0.4:
                continue

            # Check if this line updates the section context
            new_section = self._identify_section_context(line_lower)
            if new_section != "Unknown" and new_section != section_context:
                section_context = new_section

            # Extract facts from line with context
            line_facts = self._extract_from_line(line, i, text, doc_entity, section_context)
            facts.extend(line_facts)

        return json.dumps({"facts": facts})

    def _identify_document_entity(self, text: str) -> str:
        if 'delhivery' in text:
            return "Delhivery Limited"
        if 'spoton' in text:
            return "Spoton Logistics"
        if any(kw in text for kw in ['india', 'indian economy', 'rbi', 'reserve bank', 'imf', 'international monetary fund', 'economic survey']):
            return "India"
        return "Unknown Entity"

    def _identify_section_context(self, text: str) -> str:
        if 'balance sheet' in text or 'equity and liabilities' in text or 'assets' in text:
            return "Balance Sheet"
        if 'profit and loss' in text or 'income statement' in text or 'revenue' in text or 'expenses' in text:
            return "Profit & Loss"
        if 'cash flow' in text or 'cash flows' in text:
            return "Cash Flow"
        if 'proforma' in text:
            return "Proforma"
        return "Unknown"

    def _extract_from_line(self, line: str, line_idx: int, full_text: str, doc_entity: str, section: str) -> List[Dict]:
        facts = []
        line_lower = line.lower()

        # Find numbers in the line
        numbers = self.number_pattern.findall(line)
        if not numbers:
            return facts

        # Skip if line is mostly numbers (likely a header row with years)
        if len(numbers) > 5 and len(line.strip()) < 100:
            return facts

        # Determine attribute from line context + section
        attribute = self._guess_attribute_from_line(line_lower, section)
        if attribute == "Unknown Attribute":
            return facts

        unit = self._guess_unit(line_lower, line)
        time_period = self._guess_time_period(line_lower, full_text)
        scope = self._guess_scope(line_lower)
        fact_type = self._guess_fact_type(line_lower, unit)

        char_start = full_text.find(line)
        if char_start == -1:
            char_start = 0
        char_end = char_start + len(line)

        # For financial tables, the first number is often the current period, rest are comparatives
        # Take first significant number
        for num_str in numbers:
            main_value = num_str.replace(',', '')
            try:
                float(main_value)
                facts.append({
                    "entity": doc_entity,
                    "attribute": attribute,
                    "value": main_value,
                    "unit": unit,
                    "time_period": time_period,
                    "scope": scope,
                    "qualifier": f"{section}: {line[:120]}",
                    "fact_type": fact_type,
                    "confidence": 0.85 if section != "Unknown" else 0.65,
                    "evidence_span": {"start": char_start, "end": char_end}
                })
                break  # Only take first number per line for now
            except ValueError:
                continue

        return facts

    def _guess_attribute_from_line(self, line: str, section: str) -> str:
        # Balance Sheet items
        if section == "Balance Sheet":
            if 'total equity' in line or 'shareholders equity' in line or 'net worth' in line:
                return "Total Equity"
            if 'borrowings' in line and 'non-current' in line:
                return "Non-Current Borrowings"
            if 'borrowings' in line and 'current' in line:
                return "Current Borrowings"
            if 'lease liabilities' in line:
                return "Lease Liabilities"
            if 'trade payables' in line:
                return "Trade Payables"
            if 'provisions' in line and 'non-current' not in line and 'current' not in line:
                return "Provisions"
            if 'deferred tax' in line:
                return "Deferred Tax Liabilities"
            if 'total non-current liabilities' in line:
                return "Total Non-Current Liabilities"
            if 'total current liabilities' in line:
                return "Total Current Liabilities"
            if 'total equity and liabilities' in line or 'total liabilities' in line:
                return "Total Liabilities"
            if 'property, plant' in line or 'ppe' in line:
                return "Property Plant Equipment"
            if 'right of use' in line:
                return "Right of Use Assets"
            if 'intangible' in line:
                return "Intangible Assets"
            if 'investment' in line and 'non-current' in line:
                return "Non-Current Investments"
            if 'loan' in line and 'non-current' in line:
                return "Non-Current Loans"
            if 'other financial assets' in line:
                return "Other Financial Assets"
            if 'deferred tax assets' in line:
                return "Deferred Tax Assets"
            if 'inventories' in line or 'inventory' in line:
                return "Inventories"
            if 'trade receivables' in line:
                return "Trade Receivables"
            if 'cash and cash equivalents' in line or 'cash equivalents' in line:
                return "Cash & Cash Equivalents"
            if 'bank balances' in line:
                return "Bank Balances"
            if 'loans' in line and 'current' in line:
                return "Current Loans"
            if 'other current assets' in line:
                return "Other Current Assets"
            if 'total assets' in line:
                return "Total Assets"

        # Profit & Loss items
        if section == "Profit & Loss":
            if 'revenue from contract' in line or 'revenue from operations' in line:
                return "Revenue"
            if 'other income' in line:
                return "Other Income"
            if 'total income' in line:
                return "Total Income"
            if 'freight' in line and ('handling' in line or 'servicing' in line):
                return "Freight & Handling Cost"
            if 'purchase of traded' in line:
                return "Purchase of Traded Goods"
            if 'change in inventory' in line:
                return "Change in Inventory"
            if 'employee benefit' in line or 'employee cost' in line or 'salary' in line:
                return "Employee Benefit Expense"
            if 'depreciation' in line and 'amort' in line:
                return "Depreciation & Amortisation"
            if 'finance cost' in line or 'interest expense' in line:
                return "Finance Costs"
            if 'other expenses' in line:
                return "Other Expenses"
            if 'total expenses' in line:
                return "Total Expenses"
            if 'profit before tax' in line or 'loss before tax' in line:
                return "Profit Before Tax"
            if 'tax expense' in line or 'income tax' in line:
                return "Tax Expense"
            if 'profit after tax' in line or 'profit for the year' in line or 'loss for the year' in line:
                return "Profit After Tax"
            if 'other comprehensive' in line:
                return "Other Comprehensive Income"
            if 'total comprehensive' in line:
                return "Total Comprehensive Income"
            if 'ebitda' in line:
                return "EBITDA"

        # Cash Flow items
        if section == "Cash Flow":
            if 'operating activities' in line or 'cash from operations' in line:
                return "Operating Cash Flow"
            if 'investing activities' in line:
                return "Investing Cash Flow"
            if 'financing activities' in line:
                return "Financing Cash Flow"
            if 'net cash' in line:
                return "Net Cash Flow"
            if 'depreciation' in line:
                return "Depreciation (Cash Flow)"
            if 'interest received' in line:
                return "Interest Received"

        # General macroeconomic
        if 'gdp' in line and 'growth' in line:
            return "Real GDP Growth"
        if 'cpi' in line or 'consumer price' in line or 'retail inflation' in line:
            return "CPI Inflation"
        if 'fiscal deficit' in line:
            return "Fiscal Deficit"
        if 'current account' in line and 'deficit' in line:
            return "Current Account Deficit"

        return "Unknown Attribute"

    def _guess_unit(self, text: str, original: str) -> str:
        if 'percent' in text or '%' in original:
            return 'percent'
        if 'million' in text or 'mn' in text:
            return 'INR million'
        if 'crore' in text or ' cr ' in original:
            return 'INR crore'
        if 'billion' in text or 'bn' in text:
            return 'INR billion'
        if 'lakh' in text:
            return 'INR lakh'
        if 'count' in text or 'number' in text or 'nos' in text:
            return 'count'
        if 'ratio' in text or 'times' in text:
            return 'ratio'
        if 'inr' in original or 'rs.' in original or '₹' in original:
            return 'INR million'
        return 'INR million'

    def _guess_time_period(self, text: str, full_text: str) -> str:
        import re
        # Prefer the line itself so different rows/columns don't all inherit one page-level date
        for source in (text, full_text):
            fy_match = re.search(
                r'(?:FY|fiscal year|year ended)\s*(20\d{2}[-/]\d{2,4}|\d{4})',
                source,
                re.IGNORECASE,
            )
            if fy_match:
                return fy_match.group(1).replace('/', '-')
            q_match = re.search(r'(Q[1-4]\s*(?:FY|20\d{2}))', source, re.IGNORECASE)
            if q_match:
                return q_match.group(1)
            date_match = re.search(
                r'(?:march|december|june|september)\s*(?:31|30)?,?\s*20\d{2}',
                source,
                re.IGNORECASE,
            )
            if date_match:
                return date_match.group(0).strip()
        if 'nine months' in text or 'nine months' in full_text.lower():
            return 'Nine Months'
        if 'year ended' in full_text.lower():
            return 'FY'
        return 'Current'

    def _guess_scope(self, text: str) -> str:
        if 'consolidated' in text:
            return 'Consolidated'
        if 'standalone' in text or 'separate' in text:
            return 'Standalone'
        if 'proforma' in text:
            return 'Proforma'
        if 'national' in text or 'india' in text or 'central government' in text:
            return 'National'
        return 'Consolidated'

    def _guess_fact_type(self, text: str, unit: str) -> str:
        if unit == 'percent':
            return 'percentage'
        if unit == 'ratio':
            return 'ratio'
        if unit == 'count':
            return 'numeric'
        return 'numeric'


def get_extractor() -> LLMExtractor:
    extractor_type = getattr(settings, "extractor_type", "mock")

    if extractor_type == "nvidia":
        try:
            return NVIDIAExtractor()
        except Exception as e:
            logger.warning(f"NVIDIA extractor failed, falling back to mock: {e}")
            return MockExtractor()
    elif extractor_type == "ollama":
        try:
            return OllamaExtractor()
        except Exception as e:
            logger.warning(f"Ollama extractor failed, falling back to mock: {e}")
            return MockExtractor()
    else:
        return MockExtractor()


def get_entity_from_dataset(dataset: Optional[str]) -> str:
    if not dataset:
        return "Unknown Entity"
    dataset_lower = dataset.lower()
    if 'delhivery' in dataset_lower:
        return "Delhivery Limited"
    if 'spoton' in dataset_lower:
        return "Spoton Logistics"
    if 'india' in dataset_lower or 'macro' in dataset_lower or 'rbi' in dataset_lower or 'imf' in dataset_lower or 'economic' in dataset_lower:
        return "India"
    return "Unknown Entity"


class FactExtractor:
    def __init__(self, extractor: Optional[LLMExtractor] = None):
        self.llm = extractor or get_extractor()
        self.max_concurrent = settings.max_concurrent_extractions

    async def extract_from_chunk(self, chunk: Chunk, context: ExtractionContext) -> List[ExtractedFact]:
        messages = build_extraction_prompt(chunk.content, chunk.page_num, chunk.chunk_type)

        # Pass document entity hint to mock extractor
        if isinstance(self.llm, MockExtractor):
            self.llm.set_document_entity(get_entity_from_dataset(context.source_dataset))

        try:
            raw_output = await self.llm.extract(messages)
            result, errors = validate_extraction_output(raw_output)

            if errors:
                logger.warning(f"Validation errors for {context.filename} page {chunk.page_num}: {errors}")

            if result:
                valid_facts = filter_and_score_facts(result.facts, chunk.content, min_confidence=0.5)
                enriched_facts = []
                for fact in valid_facts:
                    span_start = fact.evidence_span["start"]
                    span_end = fact.evidence_span["end"]
                    fact_dict = fact.model_dump()
                    fact_dict["document_id"] = context.document_id
                    fact_dict["page_num"] = chunk.page_num
                    fact_dict["char_start"] = chunk.char_start + span_start
                    fact_dict["char_end"] = chunk.char_start + span_end
                    fact_dict["source_dataset"] = context.source_dataset
                    # Slice from chunk (includes tables) — page-text lookup alone loses table evidence
                    fact_dict["raw_evidence"] = chunk.content[span_start:span_end]
                    enriched_facts.append(ExtractedFact(**fact_dict))
                return enriched_facts
        except Exception as e:
            logger.error(f"Extraction failed for {context.filename} page {chunk.page_num}: {e}")

        return []

    async def extract_from_chunks(self, chunks: List[Chunk], context: ExtractionContext) -> List[ExtractedFact]:
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def extract_with_semaphore(chunk: Chunk) -> List[ExtractedFact]:
            async with semaphore:
                return await self.extract_from_chunk(chunk, context)

        tasks = [extract_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_facts = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Chunk {i} extraction failed: {result}")
            elif isinstance(result, list):
                all_facts.extend(result)

        return all_facts

    async def reconcile_facts(self, fact_a: Dict, fact_b: Dict) -> Dict[str, Any]:
        return await self.llm.reconcile(fact_a, fact_b)
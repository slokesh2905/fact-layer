import pdfplumber
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TableData:
    page_num: int
    bbox: tuple
    headers: List[str]
    rows: List[List[str]]
    markdown: str


@dataclass
class PageContent:
    page_num: int
    text: str
    tables: List[TableData]
    chars: List[Dict[str, Any]]
    width: float
    height: float


class PDFParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self._pdf = None

    def __enter__(self):
        self._pdf = pdfplumber.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._pdf:
            self._pdf.close()

    def get_metadata(self) -> Dict[str, Any]:
        if not self._pdf:
            self._pdf = pdfplumber.open(self.pdf_path)
        meta = self._pdf.metadata or {}
        return {
            "title": meta.get("Title"),
            "author": meta.get("Author"),
            "subject": meta.get("Subject"),
            "creator": meta.get("Creator"),
            "producer": meta.get("Producer"),
            "creation_date": meta.get("CreationDate"),
            "modification_date": meta.get("ModDate"),
            "page_count": len(self._pdf.pages),
        }

    def extract_all_pages(self) -> List[PageContent]:
        if not self._pdf:
            self._pdf = pdfplumber.open(self.pdf_path)

        pages = []
        for i, page in enumerate(self._pdf.pages):
            page_content = self._extract_page(page, i + 1)
            pages.append(page_content)
        return pages

    def _extract_page(self, page, page_num: int) -> PageContent:
        text = page.extract_text() or ""
        chars = page.chars

        tables = []
        for table in page.extract_tables(table_settings={
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "intersection_tolerance": 5,
        }):
            if table and len(table) > 1:
                headers = [str(c).strip() if c else "" for c in table[0]]
                rows = [[str(c).strip() if c else "" for c in row] for row in table[1:]]
                markdown = self._table_to_markdown(headers, rows)
                bbox = self._find_table_bbox(page, table)
                tables.append(TableData(
                    page_num=page_num,
                    bbox=bbox,
                    headers=headers,
                    rows=rows,
                    markdown=markdown
                ))

        return PageContent(
            page_num=page_num,
            text=text,
            tables=tables,
            chars=chars,
            width=page.width,
            height=page.height,
        )

    def _table_to_markdown(self, headers: List[str], rows: List[List[str]]) -> str:
        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    def _find_table_bbox(self, page, table_data) -> tuple:
        try:
            tables = page.find_tables(table_settings={
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
            })
            if tables:
                t = tables[0]
                return (t.bbox[0], t.bbox[1], t.bbox[2], t.bbox[3])
        except Exception:
            pass
        return (0, 0, page.width, page.height)

    def get_page_text(self, page_num: int) -> str:
        if not self._pdf:
            self._pdf = pdfplumber.open(self.pdf_path)
        if 1 <= page_num <= len(self._pdf.pages):
            return self._pdf.pages[page_num - 1].extract_text() or ""
        return ""

    def get_full_text(self) -> str:
        if not self._pdf:
            self._pdf = pdfplumber.open(self.pdf_path)
        texts = []
        for page in self._pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)
        return "\n\n".join(texts)
from typing import List, Dict, Any
from dataclasses import dataclass
from app.pdf.parser import PageContent, TableData
import tiktoken


@dataclass
class Chunk:
    content: str
    page_num: int
    char_start: int
    char_end: int
    chunk_type: str
    metadata: Dict[str, Any]


class Chunker:
    def __init__(self, max_tokens: int = 3000, model: str = "cl100k_base"):
        self.max_tokens = max_tokens
        self.encoding = tiktoken.get_encoding(model)

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def chunk_pages(self, pages: List[PageContent]) -> List[Chunk]:
        chunks = []
        for page in pages:
            page_chunks = self._chunk_page(page)
            chunks.extend(page_chunks)
        return chunks

    def _chunk_page(self, page: PageContent) -> List[Chunk]:
        chunks = []
        text = page.text

        if not text.strip() and not page.tables:
            return chunks

        table_texts = []
        for table in page.tables:
            table_texts.append(f"\n[TABLE Page {page.page_num}]\n{table.markdown}\n[/TABLE]")

        full_text = text + "\n".join(table_texts)

        if self.count_tokens(full_text) <= self.max_tokens:
            chunks.append(Chunk(
                content=full_text,
                page_num=page.page_num,
                char_start=0,
                char_end=len(text),
                chunk_type="page",
                metadata={"has_tables": len(page.tables) > 0, "table_count": len(page.tables)}
            ))
        else:
            chunks.extend(self._split_text(full_text, page.page_num, text))

        for i, table in enumerate(page.tables):
            chunks.append(Chunk(
                content=f"\n[TABLE Page {page.page_num}]\n{table.markdown}\n[/TABLE]",
                page_num=page.page_num,
                char_start=0,
                char_end=0,
                chunk_type="table",
                metadata={"table_index": i, "headers": table.headers, "row_count": len(table.rows)}
            ))

        return chunks

    def _split_text(self, text: str, page_num: int, original_text: str) -> List[Chunk]:
        chunks = []
        paragraphs = text.split("\n\n")
        current_chunk = ""
        current_start = 0

        for para in paragraphs:
            test_chunk = current_chunk + "\n\n" + para if current_chunk else para
            if self.count_tokens(test_chunk) <= self.max_tokens:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    char_end = current_start + len(current_chunk)
                    chunks.append(Chunk(
                        content=current_chunk,
                        page_num=page_num,
                        char_start=current_start,
                        char_end=min(char_end, len(original_text)),
                        chunk_type="page_part",
                        metadata={}
                    ))
                    current_start = char_end
                current_chunk = para

        if current_chunk:
            char_end = current_start + len(current_chunk)
            chunks.append(Chunk(
                content=current_chunk,
                page_num=page_num,
                char_start=current_start,
                char_end=min(char_end, len(original_text)),
                chunk_type="page_part",
                metadata={}
            ))

        return chunks
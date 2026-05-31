from uuid import UUID

from regintel_domain import Chunk
from regintel_infrastructure.chunking.regulation_chunker import (
    build_chunks_from_pages,
    build_chunks_from_text,
)
from regintel_infrastructure.parsing.docx_parser import parse_docx
from regintel_infrastructure.parsing.pdf_parser import parse_pdf


def parse_and_chunk(filename: str, content: bytes, document_id: UUID) -> list[Chunk]:
    """Dispatches to the right parser by file extension, then chunks the result.
    The one place that needs to know both parsing and chunking exist, so callers
    (the API upload route today) don't have to branch on file type themselves.
    """
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        pages = parse_pdf(content)
        return build_chunks_from_pages(document_id, pages)
    if lower_name.endswith(".docx"):
        text = parse_docx(content)
        return build_chunks_from_text(document_id, text)
    raise ValueError(f"unsupported file type: {filename!r} (expected .pdf or .docx)")

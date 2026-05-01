import re
from dataclasses import dataclass
from uuid import UUID, uuid4

from regintel_domain import Chunk
from regintel_infrastructure.parsing.pdf_parser import ParsedPage

# Matches numbered clause headers as used in RBI circulars/master directions,
# e.g. "3.", "3.1", "3.1.2" at the start of a paragraph.
_CLAUSE_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

_MIN_CHUNK_CHARS = 200
_MAX_CHUNK_CHARS = 1000


@dataclass(frozen=True)
class ChunkDraft:
    content: str
    clause_reference: str | None
    page_number: int | None


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _detect_clause(paragraph: str) -> str | None:
    match = _CLAUSE_PATTERN.match(paragraph)
    return match.group(1) if match else None


def _split_oversized(paragraph: str) -> list[str]:
    """A single paragraph with no internal blank-line break can still exceed
    _MAX_CHUNK_CHARS on its own — split it at sentence boundaries so it never
    becomes one oversized, low-precision chunk."""
    if len(paragraph) <= _MAX_CHUNK_CHARS:
        return [paragraph]

    pieces: list[str] = []
    buffer = ""
    for sentence in _SENTENCE_BOUNDARY.split(paragraph):
        candidate = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(candidate) > _MAX_CHUNK_CHARS and buffer:
            pieces.append(buffer)
            buffer = sentence
        else:
            buffer = candidate
    if buffer:
        pieces.append(buffer)
    return pieces


def _merge_undersized_drafts(drafts: list[ChunkDraft]) -> list[ChunkDraft]:
    """Merges any chunk shorter than _MIN_CHUNK_CHARS into the one that follows it,
    so a lone short paragraph never becomes a low-context chunk on its own."""
    merged: list[ChunkDraft] = []
    pending: ChunkDraft | None = None

    for draft in drafts:
        if pending is None:
            pending = draft
            continue
        if len(pending.content) < _MIN_CHUNK_CHARS:
            pending = ChunkDraft(
                content=f"{pending.content}\n\n{draft.content}",
                clause_reference=pending.clause_reference or draft.clause_reference,
                page_number=pending.page_number,
            )
        else:
            merged.append(pending)
            pending = draft

    if pending is not None:
        merged.append(pending)

    return merged


def chunk_text(text: str, page_number: int | None = None) -> list[ChunkDraft]:
    """Splits text into chunks aligned to clause boundaries where detectable,
    falling back to paragraph grouping otherwise. A chunk is flushed whenever a
    new clause starts or the running buffer exceeds _MAX_CHUNK_CHARS, then
    undersized chunks are merged forward so fragments stay contextual.

    current_clause is intentionally NOT reset on every flush — a single clause
    whose content is long enough to span multiple chunks should have every one
    of those chunks carry the same clause_reference, not lose it after the
    first split.
    """
    drafts: list[ChunkDraft] = []
    buffer = ""
    current_clause: str | None = None

    def flush() -> None:
        nonlocal buffer
        if buffer:
            drafts.append(
                ChunkDraft(
                    content=buffer.strip(), clause_reference=current_clause, page_number=page_number
                )
            )
        buffer = ""

    for paragraph in _split_paragraphs(text):
        clause = _detect_clause(paragraph)
        if clause is not None:
            flush()
            current_clause = clause

        for piece in _split_oversized(paragraph):
            candidate = f"{buffer}\n\n{piece}" if buffer else piece
            if len(candidate) > _MAX_CHUNK_CHARS and buffer:
                flush()
                buffer = piece
            else:
                buffer = candidate

            if len(buffer) >= _MAX_CHUNK_CHARS:
                flush()

    flush()

    return _merge_undersized_drafts(drafts)


def _drafts_to_chunks(document_id: UUID, drafts: list[ChunkDraft], start_index: int) -> list[Chunk]:
    return [
        Chunk(
            id=uuid4(),
            document_id=document_id,
            content=draft.content,
            chunk_index=start_index + offset,
            clause_reference=draft.clause_reference,
            page_number=draft.page_number,
        )
        for offset, draft in enumerate(drafts)
    ]


def build_chunks_from_pages(document_id: UUID, pages: list[ParsedPage]) -> list[Chunk]:
    """Chunks a PDF's pages independently, preserving each chunk's source page number."""
    chunks: list[Chunk] = []
    for page in pages:
        drafts = chunk_text(page.text, page_number=page.page_number)
        chunks.extend(_drafts_to_chunks(document_id, drafts, start_index=len(chunks)))
    return chunks


def build_chunks_from_text(document_id: UUID, text: str) -> list[Chunk]:
    """Chunks a single block of text with no page concept (e.g. a DOCX)."""
    drafts = chunk_text(text, page_number=None)
    return _drafts_to_chunks(document_id, drafts, start_index=0)

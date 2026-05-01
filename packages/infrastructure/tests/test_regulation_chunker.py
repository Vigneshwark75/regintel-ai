from uuid import uuid4

from regintel_infrastructure.chunking.regulation_chunker import (
    build_chunks_from_pages,
    build_chunks_from_text,
    chunk_text,
)
from regintel_infrastructure.parsing.pdf_parser import ParsedPage

_SAMPLE_TEXT = """1. Applicability

This Master Direction applies to all Non-Banking Financial Companies (NBFCs)
registered with the Reserve Bank of India under Section 45-IA of the RBI Act,
1934, and to all branches and offices of such NBFCs.

2. Customer Due Diligence

2.1 Regulated entities shall undertake Customer Due Diligence (CDD) measures
while commencing an account-based relationship with a customer, carrying out
occasional transactions above the prescribed threshold, or when there is a
suspicion of money laundering or terrorist financing.

2.2 Regulated entities shall maintain updated KYC records for all existing
customers on the basis of materiality and risk, in accordance with the
periodic updation timelines specified in this Direction.
"""


def test_chunk_text_detects_clause_headers() -> None:
    drafts = chunk_text(_SAMPLE_TEXT)

    clause_references = [d.clause_reference for d in drafts if d.clause_reference is not None]
    assert "1" in clause_references
    assert "2" in clause_references


def test_chunk_text_returns_no_chunks_for_blank_text() -> None:
    assert chunk_text("   \n\n   ") == []


def test_chunk_text_merges_short_trailing_fragment_forward() -> None:
    drafts = chunk_text("1. Short clause.\n\n2. Also short.")

    # Neither clause alone reaches _MIN_CHUNK_CHARS, so they should merge into one chunk.
    assert len(drafts) == 1
    assert drafts[0].clause_reference == "1"


def test_chunk_text_splits_a_very_long_unnumbered_block() -> None:
    long_paragraph = "General guidance text without numbering. " * 60
    drafts = chunk_text(long_paragraph)

    assert len(drafts) > 1
    assert all(len(d.content) <= 1000 for d in drafts)


def test_chunk_text_preserves_clause_reference_across_a_long_clauses_splits() -> None:
    long_clause = "3. " + "Regulated entities shall maintain detailed KYC records. " * 30

    drafts = chunk_text(long_clause)

    assert len(drafts) > 1
    assert all(d.clause_reference == "3" for d in drafts)


def test_build_chunks_from_pages_preserves_page_numbers() -> None:
    document_id = uuid4()
    pages = [
        ParsedPage(page_number=1, text=_SAMPLE_TEXT),
        ParsedPage(page_number=2, text=_SAMPLE_TEXT),
    ]

    chunks = build_chunks_from_pages(document_id, pages)

    assert {c.page_number for c in chunks} == {1, 2}
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.document_id == document_id for c in chunks)


def test_build_chunks_from_text_has_no_page_numbers() -> None:
    document_id = uuid4()

    chunks = build_chunks_from_text(document_id, _SAMPLE_TEXT)

    assert all(c.page_number is None for c in chunks)
    assert len(chunks) > 0

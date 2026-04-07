from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from regintel_domain.enums import DocumentType


class Document(BaseModel):
    """A single ingested regulatory file (one PDF/DOCX upload)."""

    id: UUID
    title: str = Field(min_length=1)
    document_type: DocumentType
    reference_number: str = Field(min_length=1)
    issued_date: date
    source_url: str | None = None


class Chunk(BaseModel):
    """A retrievable slice of a Document's text, produced by the ingestion pipeline."""

    id: UUID
    document_id: UUID
    content: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    clause_reference: str | None = None
    page_number: int | None = Field(default=None, ge=1)

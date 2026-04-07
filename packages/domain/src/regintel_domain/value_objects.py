from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    """A grounded pointer from an answer back to the exact source text it came from.

    Immutable — a citation describes a fact about a chunk at answer-time and
    should never be mutated after an answer is recorded.
    """

    model_config = ConfigDict(frozen=True)

    document_id: UUID
    chunk_id: UUID
    quoted_text: str = Field(min_length=1)
    clause_reference: str | None = None
    page_number: int | None = Field(default=None, ge=1)

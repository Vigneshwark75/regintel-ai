from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class RegulationVersion(BaseModel):
    """Places one Document in the chronological lineage of a named regulation.

    A "regulation" (e.g. "Master Direction — KYC") is amended over time by
    multiple documents. This entity is what lets the compare/diff use case
    ask "what changed between version N and version N+1 of X" without the
    Document entity itself needing to know about versioning.
    """

    id: UUID
    regulation_name: str = Field(min_length=1)
    document_id: UUID
    version_number: int = Field(ge=1)
    effective_date: date
    is_current: bool = True

    def supersede(self) -> None:
        self.is_current = False

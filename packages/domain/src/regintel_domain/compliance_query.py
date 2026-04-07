from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from regintel_domain.enums import UserRole
from regintel_domain.value_objects import Citation


class ComplianceQuery(BaseModel):
    """A natural-language question asked by a user and its grounded answer.

    Enforces the platform's core promise: an answer is not recorded unless
    it carries at least one citation back to source material.
    """

    id: UUID
    asked_by_role: UserRole
    question: str = Field(min_length=1)
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime
    answered_at: datetime | None = None

    def record_answer(self, answer: str, citations: list[Citation]) -> None:
        if not citations:
            raise ValueError("an answer must be grounded in at least one citation")
        self.answer = answer
        self.citations = citations
        self.answered_at = datetime.now(UTC)

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from regintel_domain.enums import ActionItemPriority, ActionItemStatus, UserRole
from regintel_domain.value_objects import Citation


class ActionItem(BaseModel):
    """A concrete compliance task derived from a regulation, always traceable
    back to the clauses that justify it — an action item with no citations
    is not a valid one.
    """

    id: UUID
    description: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)
    owner_role: UserRole
    priority: ActionItemPriority
    status: ActionItemStatus = ActionItemStatus.OPEN
    due_date: date | None = None
    dismissal_reason: str | None = None
    created_at: datetime

    def start(self) -> None:
        if self.status == ActionItemStatus.DISMISSED:
            raise ValueError("cannot start a dismissed action item")
        self.status = ActionItemStatus.IN_PROGRESS

    def complete(self) -> None:
        if self.status == ActionItemStatus.DISMISSED:
            raise ValueError("cannot complete a dismissed action item")
        self.status = ActionItemStatus.DONE

    def dismiss(self, reason: str) -> None:
        if not reason.strip():
            raise ValueError("a dismissal reason is required")
        self.status = ActionItemStatus.DISMISSED
        self.dismissal_reason = reason

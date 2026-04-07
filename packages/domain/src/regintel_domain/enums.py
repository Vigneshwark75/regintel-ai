from enum import StrEnum


class DocumentType(StrEnum):
    CIRCULAR = "circular"
    MASTER_DIRECTION = "master_direction"
    NOTIFICATION = "notification"
    FAQ = "faq"
    GUIDELINE = "guideline"


class UserRole(StrEnum):
    CRO = "cro"
    COMPLIANCE_OFFICER = "compliance_officer"
    RISK = "risk"
    AUDITOR = "auditor"
    OPS = "ops"


class ActionItemStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    DISMISSED = "dismissed"


class ActionItemPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

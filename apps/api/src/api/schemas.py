from uuid import UUID

from pydantic import BaseModel

from regintel_domain import ActionItemPriority, ActionItemStatus, Citation, UserRole


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    chunk_count: int


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]


class CompareRequest(BaseModel):
    document_id_a: UUID
    document_id_b: UUID


class CompareResponse(BaseModel):
    comparison: str


class SummarizeResponse(BaseModel):
    summary: str


class GenerateActionItemsRequest(BaseModel):
    topic: str
    owner_role: UserRole


class ActionItemResponse(BaseModel):
    id: UUID
    description: str
    citations: list[Citation]
    owner_role: UserRole
    priority: ActionItemPriority
    status: ActionItemStatus


class GenerateActionItemsResponse(BaseModel):
    action_items: list[ActionItemResponse]

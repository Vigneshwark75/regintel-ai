from typing import Protocol
from uuid import UUID

from regintel_domain import Chunk, Document


class DocumentRepository(Protocol):
    """Persistence port for Documents and their Chunks.

    Deliberately scoped to what ingestion and retrieval need. Repositories for
    RegulationVersion, ActionItem, and ComplianceQuery are added alongside the
    use cases that first need them, not speculatively ahead of that.
    """

    async def save_document(self, document: Document) -> None: ...

    async def get_document(self, document_id: UUID) -> Document | None: ...

    async def save_chunks(self, chunks: list[Chunk]) -> None: ...

    async def get_chunks_by_document(self, document_id: UUID) -> list[Chunk]: ...

    async def get_chunks_by_ids(self, chunk_ids: list[UUID]) -> list[Chunk]: ...

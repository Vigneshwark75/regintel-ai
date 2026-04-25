from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from regintel_domain import Chunk, Document, DocumentType
from regintel_infrastructure.db.models import ChunkModel, DocumentModel


def _document_to_model(document: Document) -> DocumentModel:
    return DocumentModel(
        id=document.id,
        title=document.title,
        document_type=document.document_type.value,
        reference_number=document.reference_number,
        issued_date=document.issued_date,
        source_url=document.source_url,
    )


def _model_to_document(model: DocumentModel) -> Document:
    return Document(
        id=model.id,
        title=model.title,
        document_type=DocumentType(model.document_type),
        reference_number=model.reference_number,
        issued_date=model.issued_date,
        source_url=model.source_url,
    )


def _chunk_to_model(chunk: Chunk) -> ChunkModel:
    return ChunkModel(
        id=chunk.id,
        document_id=chunk.document_id,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
        clause_reference=chunk.clause_reference,
        page_number=chunk.page_number,
    )


def _model_to_chunk(model: ChunkModel) -> Chunk:
    return Chunk(
        id=model.id,
        document_id=model.document_id,
        content=model.content,
        chunk_index=model.chunk_index,
        clause_reference=model.clause_reference,
        page_number=model.page_number,
    )


class PostgresDocumentRepository:
    """Implements the application layer's DocumentRepository port against Postgres."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_document(self, document: Document) -> None:
        await self._session.merge(_document_to_model(document))

    async def get_document(self, document_id: UUID) -> Document | None:
        model = await self._session.get(DocumentModel, document_id)
        return _model_to_document(model) if model is not None else None

    async def save_chunks(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            await self._session.merge(_chunk_to_model(chunk))

    async def get_chunks_by_document(self, document_id: UUID) -> list[Chunk]:
        result = await self._session.execute(
            select(ChunkModel)
            .where(ChunkModel.document_id == document_id)
            .order_by(ChunkModel.chunk_index)
        )
        return [_model_to_chunk(model) for model in result.scalars().all()]

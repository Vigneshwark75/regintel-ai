from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

import pytest

from regintel_application.ports.vector_store import SparseVector, VectorEntry
from regintel_application.use_cases.ingest_document import IngestDocumentUseCase
from regintel_domain import Chunk, Document, DocumentType


@dataclass
class FakeDocumentRepository:
    documents: dict[UUID, Document] = field(default_factory=dict)
    chunks: dict[UUID, list[Chunk]] = field(default_factory=dict)

    async def save_document(self, document: Document) -> None:
        self.documents[document.id] = document

    async def get_document(self, document_id: UUID) -> Document | None:
        return self.documents.get(document_id)

    async def save_chunks(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self.chunks.setdefault(chunk.document_id, []).append(chunk)

    async def get_chunks_by_document(self, document_id: UUID) -> list[Chunk]:
        return self.chunks.get(document_id, [])


@dataclass
class FakeVectorStore:
    upserted: list[VectorEntry] = field(default_factory=list)

    async def ensure_collection(self) -> None:
        pass

    async def upsert_chunks(self, entries: list[VectorEntry]) -> None:
        self.upserted.extend(entries)

    async def search(
        self, dense_vector: list[float], sparse_vector: SparseVector, limit: int = 10
    ) -> list[object]:
        return []

    async def delete_by_document(self, document_id: UUID) -> None:
        self.upserted = [e for e in self.upserted if e.document_id != document_id]


class FakeEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]


class FakeSparseEmbeddingProvider:
    async def embed_sparse(self, texts: list[str]) -> list[SparseVector]:
        return [SparseVector(indices=[0], values=[float(len(text))]) for text in texts]


def make_document() -> Document:
    return Document(
        id=uuid4(),
        title="Master Direction on KYC",
        document_type=DocumentType.MASTER_DIRECTION,
        reference_number="RBI/DBR/2016-17/18",
        issued_date=date(2016, 2, 25),
    )


def make_chunks(document_id: UUID, count: int = 2) -> list[Chunk]:
    return [
        Chunk(id=uuid4(), document_id=document_id, content=f"clause {i} text", chunk_index=i)
        for i in range(count)
    ]


async def test_ingest_persists_document_and_chunks() -> None:
    document_repository = FakeDocumentRepository()
    use_case = IngestDocumentUseCase(
        document_repository=document_repository,
        vector_store=FakeVectorStore(),
        embedding_provider=FakeEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
    )
    document = make_document()
    chunks = make_chunks(document.id)

    await use_case.execute(document, chunks)

    assert document_repository.documents[document.id] == document
    assert document_repository.chunks[document.id] == chunks


async def test_ingest_upserts_one_vector_entry_per_chunk() -> None:
    vector_store = FakeVectorStore()
    use_case = IngestDocumentUseCase(
        document_repository=FakeDocumentRepository(),
        vector_store=vector_store,
        embedding_provider=FakeEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
    )
    document = make_document()
    chunks = make_chunks(document.id, count=3)

    await use_case.execute(document, chunks)

    assert {entry.chunk_id for entry in vector_store.upserted} == {c.id for c in chunks}


async def test_ingest_rejects_a_document_with_no_chunks() -> None:
    use_case = IngestDocumentUseCase(
        document_repository=FakeDocumentRepository(),
        vector_store=FakeVectorStore(),
        embedding_provider=FakeEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
    )

    with pytest.raises(ValueError, match="at least one chunk"):
        await use_case.execute(make_document(), [])

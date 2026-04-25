from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class SparseVector:
    """A BM25-style sparse vector: parallel arrays of term indices and weights."""

    indices: list[int]
    values: list[float]


@dataclass(frozen=True)
class VectorEntry:
    """One chunk's dense + sparse vectors, ready to upsert into the vector store."""

    chunk_id: UUID
    document_id: UUID
    dense_vector: list[float]
    sparse_vector: SparseVector


@dataclass(frozen=True)
class SearchHit:
    chunk_id: UUID
    document_id: UUID
    score: float


class VectorStore(Protocol):
    """Persistence port for chunk embeddings and hybrid (dense + sparse) search.

    Implementations own how dense/sparse results are fused (e.g. RRF) — callers
    just get back a single ranked list.
    """

    async def ensure_collection(self) -> None: ...

    async def upsert_chunks(self, entries: list[VectorEntry]) -> None: ...

    async def search(
        self, dense_vector: list[float], sparse_vector: SparseVector, limit: int = 10
    ) -> list[SearchHit]: ...

    async def delete_by_document(self, document_id: UUID) -> None: ...

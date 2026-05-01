from typing import Protocol

from regintel_application.ports.vector_store import SparseVector


class EmbeddingProvider(Protocol):
    """Dense embedding port — e.g. OpenAI text-embedding-3-large."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class SparseEmbeddingProvider(Protocol):
    """Sparse (BM25-style) embedding port, kept separate from EmbeddingProvider since
    it's a distinct concern with a distinct swap point (e.g. local BM25 vs SPLADE)."""

    async def embed_sparse(self, texts: list[str]) -> list[SparseVector]: ...

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from regintel_application.ports.reranker import RerankedChunk
from regintel_application.ports.vector_store import SearchHit, SparseVector
from regintel_application.use_cases.retrieve_chunks import RetrieveChunksUseCase
from regintel_domain import Chunk


@dataclass
class FakeDocumentRepository:
    chunks_by_id: dict[UUID, Chunk] = field(default_factory=dict)

    async def save_document(self, document: object) -> None:
        raise NotImplementedError

    async def get_document(self, document_id: UUID) -> None:
        raise NotImplementedError

    async def save_chunks(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError

    async def get_chunks_by_document(self, document_id: UUID) -> list[Chunk]:
        raise NotImplementedError

    async def get_chunks_by_ids(self, chunk_ids: list[UUID]) -> list[Chunk]:
        return [self.chunks_by_id[cid] for cid in chunk_ids if cid in self.chunks_by_id]


@dataclass
class FakeVectorStore:
    hits: list[SearchHit] = field(default_factory=list)

    async def ensure_collection(self) -> None:
        pass

    async def upsert_chunks(self, entries: list[object]) -> None:
        raise NotImplementedError

    async def search(
        self, dense_vector: list[float], sparse_vector: SparseVector, limit: int = 10
    ) -> list[SearchHit]:
        return self.hits[:limit]

    async def delete_by_document(self, document_id: UUID) -> None:
        raise NotImplementedError


class FakeEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]


class FakeSparseEmbeddingProvider:
    async def embed_sparse(self, texts: list[str]) -> list[SparseVector]:
        return [SparseVector(indices=[0], values=[1.0]) for _ in texts]


@dataclass
class FakeReranker:
    """Reverses input order, to prove the use case returns reranker order, not fetch order."""

    async def rerank(self, query: str, chunks: list[Chunk], top_n: int) -> list[RerankedChunk]:
        return [RerankedChunk(chunk=c, score=float(i)) for i, c in enumerate(reversed(chunks))][
            :top_n
        ]


def make_chunk(document_id: UUID, content: str = "some clause text") -> Chunk:
    return Chunk(id=uuid4(), document_id=document_id, content=content, chunk_index=0)


async def test_retrieve_returns_no_citations_when_vector_store_has_no_hits() -> None:
    use_case = RetrieveChunksUseCase(
        document_repository=FakeDocumentRepository(),
        vector_store=FakeVectorStore(hits=[]),
        embedding_provider=FakeEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
        reranker=FakeReranker(),
    )

    citations = await use_case.execute("what is the KYC threshold?")

    assert citations == []


async def test_retrieve_returns_citations_in_reranked_order() -> None:
    document_id = uuid4()
    chunk_a = make_chunk(document_id, content="first chunk")
    chunk_b = make_chunk(document_id, content="second chunk")
    repository = FakeDocumentRepository(chunks_by_id={chunk_a.id: chunk_a, chunk_b.id: chunk_b})
    vector_store = FakeVectorStore(
        hits=[
            SearchHit(chunk_id=chunk_a.id, document_id=document_id, score=0.9),
            SearchHit(chunk_id=chunk_b.id, document_id=document_id, score=0.8),
        ]
    )
    use_case = RetrieveChunksUseCase(
        document_repository=repository,
        vector_store=vector_store,
        embedding_provider=FakeEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
        reranker=FakeReranker(),
    )

    citations = await use_case.execute("query", top_n=2)

    # FakeReranker reverses order, so chunk_b's citation should come first.
    assert [c.chunk_id for c in citations] == [chunk_b.id, chunk_a.id]
    assert citations[0].quoted_text == "second chunk"


async def test_retrieve_respects_top_n_truncation() -> None:
    document_id = uuid4()
    chunks = [make_chunk(document_id, content=f"chunk {i}") for i in range(5)]
    repository = FakeDocumentRepository(chunks_by_id={c.id: c for c in chunks})
    vector_store = FakeVectorStore(
        hits=[SearchHit(chunk_id=c.id, document_id=document_id, score=1.0) for c in chunks]
    )
    use_case = RetrieveChunksUseCase(
        document_repository=repository,
        vector_store=vector_store,
        embedding_provider=FakeEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
        reranker=FakeReranker(),
    )

    citations = await use_case.execute("query", top_n=2)

    assert len(citations) == 2

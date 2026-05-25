from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from regintel_application.ports.llm_provider import LLMMessage, LLMResponse
from regintel_application.ports.reranker import RerankedChunk
from regintel_application.ports.vector_store import SearchHit, SparseVector
from regintel_application.use_cases.generate_action_items import GenerateActionItemsUseCase
from regintel_application.use_cases.retrieve_chunks import RetrieveChunksUseCase
from regintel_domain import ActionItemStatus, Chunk, UserRole


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
class IdentityReranker:
    async def rerank(self, query: str, chunks: list[Chunk], top_n: int) -> list[RerankedChunk]:
        return [RerankedChunk(chunk=c, score=1.0) for c in chunks[:top_n]]


@dataclass
class FakeLLMProvider:
    response_content: str

    async def complete(
        self, messages: list[LLMMessage], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        return LLMResponse(content=self.response_content, tool_calls=[])


def make_chunk(document_id: UUID, content: str) -> Chunk:
    return Chunk(id=uuid4(), document_id=document_id, content=content, chunk_index=0)


def make_retrieve_chunks_use_case(chunks: list[Chunk]) -> RetrieveChunksUseCase:
    document_id = chunks[0].document_id if chunks else uuid4()
    return RetrieveChunksUseCase(
        document_repository=FakeDocumentRepository(chunks_by_id={c.id: c for c in chunks}),
        vector_store=FakeVectorStore(
            hits=[SearchHit(chunk_id=c.id, document_id=document_id, score=1.0) for c in chunks]
        ),
        embedding_provider=FakeEmbeddingProvider(),
        sparse_embedding_provider=FakeSparseEmbeddingProvider(),
        reranker=IdentityReranker(),
    )


async def test_generate_action_items_grounds_each_item_to_its_cited_indices() -> None:
    document_id = uuid4()
    chunks = [make_chunk(document_id, f"clause {i}") for i in range(3)]
    retrieve = make_retrieve_chunks_use_case(chunks)
    llm = FakeLLMProvider(
        response_content=(
            '[{"description": "Update policy", "priority": "high", "citation_indices": [0]}]'
        )
    )
    use_case = GenerateActionItemsUseCase(retrieve_chunks=retrieve, llm_provider=llm)

    items = await use_case.execute("some topic", UserRole.COMPLIANCE_OFFICER)

    assert len(items) == 1
    assert items[0].description == "Update policy"
    assert len(items[0].citations) == 1
    assert items[0].status == ActionItemStatus.OPEN


async def test_generate_action_items_skips_ungrounded_proposals() -> None:
    document_id = uuid4()
    chunks = [make_chunk(document_id, f"clause {i}") for i in range(3)]
    retrieve = make_retrieve_chunks_use_case(chunks)
    llm = FakeLLMProvider(
        response_content='[{"description": "No support", "priority": "low", "citation_indices": []}]'
    )
    use_case = GenerateActionItemsUseCase(retrieve_chunks=retrieve, llm_provider=llm)

    items = await use_case.execute("some topic", UserRole.RISK)

    assert items == []


async def test_generate_action_items_returns_empty_list_when_nothing_retrieved() -> None:
    retrieve = make_retrieve_chunks_use_case([])
    llm = FakeLLMProvider(response_content="[]")
    use_case = GenerateActionItemsUseCase(retrieve_chunks=retrieve, llm_provider=llm)

    items = await use_case.execute("some topic", UserRole.OPS)

    assert items == []


async def test_generate_action_items_raises_on_invalid_json() -> None:
    document_id = uuid4()
    chunks = [make_chunk(document_id, "clause")]
    retrieve = make_retrieve_chunks_use_case(chunks)
    llm = FakeLLMProvider(response_content="not json")
    use_case = GenerateActionItemsUseCase(retrieve_chunks=retrieve, llm_provider=llm)

    with pytest.raises(ValueError, match="valid JSON"):
        await use_case.execute("some topic", UserRole.CRO)

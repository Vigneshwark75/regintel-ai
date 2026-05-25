from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from regintel_application.ports.llm_provider import LLMMessage, LLMResponse
from regintel_application.use_cases.summarize_regulation import SummarizeRegulationUseCase
from regintel_domain import Chunk


@dataclass
class FakeDocumentRepository:
    chunks_by_document: dict[UUID, list[Chunk]] = field(default_factory=dict)

    async def save_document(self, document: object) -> None:
        raise NotImplementedError

    async def get_document(self, document_id: UUID) -> None:
        raise NotImplementedError

    async def save_chunks(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError

    async def get_chunks_by_document(self, document_id: UUID) -> list[Chunk]:
        return self.chunks_by_document.get(document_id, [])

    async def get_chunks_by_ids(self, chunk_ids: list[UUID]) -> list[Chunk]:
        raise NotImplementedError


@dataclass
class FakeLLMProvider:
    response_content: str
    received_messages: list[LLMMessage] = field(default_factory=list)

    async def complete(
        self, messages: list[LLMMessage], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        self.received_messages = messages
        return LLMResponse(content=self.response_content, tool_calls=[])


def make_chunk(document_id: UUID, content: str) -> Chunk:
    return Chunk(id=uuid4(), document_id=document_id, content=content, chunk_index=0)


async def test_summarize_returns_the_llm_response() -> None:
    document_id = uuid4()
    repository = FakeDocumentRepository(
        chunks_by_document={document_id: [make_chunk(document_id, "clause text")]}
    )
    llm = FakeLLMProvider(response_content="This regulation requires X.")
    use_case = SummarizeRegulationUseCase(document_repository=repository, llm_provider=llm)

    summary = await use_case.execute(document_id)

    assert summary == "This regulation requires X."


async def test_summarize_includes_all_chunk_content_in_the_prompt() -> None:
    document_id = uuid4()
    repository = FakeDocumentRepository(
        chunks_by_document={
            document_id: [
                make_chunk(document_id, "first clause"),
                make_chunk(document_id, "second clause"),
            ]
        }
    )
    llm = FakeLLMProvider(response_content="summary")
    use_case = SummarizeRegulationUseCase(document_repository=repository, llm_provider=llm)

    await use_case.execute(document_id)

    user_message = next(m for m in llm.received_messages if m.role == "user")
    assert "first clause" in user_message.content
    assert "second clause" in user_message.content


async def test_summarize_raises_for_a_document_with_no_ingested_chunks() -> None:
    repository = FakeDocumentRepository()
    llm = FakeLLMProvider(response_content="unused")
    use_case = SummarizeRegulationUseCase(document_repository=repository, llm_provider=llm)

    with pytest.raises(ValueError, match="no ingested chunks"):
        await use_case.execute(uuid4())

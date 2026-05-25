from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from regintel_application.ports.llm_provider import LLMMessage, LLMResponse
from regintel_application.use_cases.compare_regulations import CompareRegulationsUseCase
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


async def test_compare_returns_the_llm_response() -> None:
    doc_a, doc_b = uuid4(), uuid4()
    repository = FakeDocumentRepository(
        chunks_by_document={
            doc_a: [make_chunk(doc_a, "old threshold: 50000")],
            doc_b: [make_chunk(doc_b, "new threshold: 100000")],
        }
    )
    llm = FakeLLMProvider(response_content="The threshold doubled.")
    use_case = CompareRegulationsUseCase(document_repository=repository, llm_provider=llm)

    result = await use_case.execute(doc_a, doc_b)

    assert result == "The threshold doubled."


async def test_compare_includes_both_documents_text_in_the_prompt() -> None:
    doc_a, doc_b = uuid4(), uuid4()
    repository = FakeDocumentRepository(
        chunks_by_document={
            doc_a: [make_chunk(doc_a, "old threshold text")],
            doc_b: [make_chunk(doc_b, "new threshold text")],
        }
    )
    llm = FakeLLMProvider(response_content="unused")
    use_case = CompareRegulationsUseCase(document_repository=repository, llm_provider=llm)

    await use_case.execute(doc_a, doc_b)

    user_message = next(m for m in llm.received_messages if m.role == "user")
    assert "old threshold text" in user_message.content
    assert "new threshold text" in user_message.content


async def test_compare_raises_when_either_document_has_no_chunks() -> None:
    doc_a, doc_b = uuid4(), uuid4()
    repository = FakeDocumentRepository(chunks_by_document={doc_a: [make_chunk(doc_a, "text")]})
    llm = FakeLLMProvider(response_content="unused")
    use_case = CompareRegulationsUseCase(document_repository=repository, llm_provider=llm)

    with pytest.raises(ValueError, match="both documents"):
        await use_case.execute(doc_a, doc_b)

from uuid import uuid4

import pytest

from regintel_domain import Chunk
from regintel_infrastructure.reranking.local_cross_encoder_reranker import LocalCrossEncoderReranker

pytestmark = pytest.mark.integration


def make_chunk(content: str) -> Chunk:
    return Chunk(id=uuid4(), document_id=uuid4(), content=content, chunk_index=0)


async def test_rerank_ranks_the_relevant_chunk_first() -> None:
    reranker = LocalCrossEncoderReranker()
    relevant = make_chunk(
        "Regulated entities shall maintain KYC records for all customers as per this Direction."
    )
    irrelevant = make_chunk("The weather in Mumbai is expected to be hot this week.")

    results = await reranker.rerank(
        "What are the KYC record-keeping requirements?", [irrelevant, relevant], top_n=2
    )

    assert results[0].chunk.id == relevant.id
    assert results[0].score > results[1].score


async def test_rerank_respects_top_n() -> None:
    reranker = LocalCrossEncoderReranker()
    chunks = [make_chunk(f"clause {i} about KYC obligations") for i in range(5)]

    results = await reranker.rerank("KYC obligations", chunks, top_n=2)

    assert len(results) == 2


async def test_rerank_returns_empty_list_for_no_candidates() -> None:
    reranker = LocalCrossEncoderReranker()

    assert await reranker.rerank("query", [], top_n=5) == []

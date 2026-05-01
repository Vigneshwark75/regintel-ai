import pytest

from regintel_infrastructure.embeddings.bm25_sparse_provider import Bm25SparseEmbeddingProvider

# Not Docker-dependent, but downloads real model weights on first run — grouped with
# integration tests so `make test` stays instant and offline-safe.
pytestmark = pytest.mark.integration


async def test_embed_sparse_returns_one_vector_per_text() -> None:
    provider = Bm25SparseEmbeddingProvider()

    vectors = await provider.embed_sparse(["customer due diligence", "know your customer"])

    assert len(vectors) == 2
    assert all(len(v.indices) == len(v.values) for v in vectors)
    assert all(len(v.indices) > 0 for v in vectors)


async def test_embed_sparse_gives_shared_terms_matching_indices() -> None:
    provider = Bm25SparseEmbeddingProvider()

    vectors = await provider.embed_sparse(["customer due diligence", "customer onboarding"])

    shared_indices = set(vectors[0].indices) & set(vectors[1].indices)
    assert shared_indices, "expected the shared term 'customer' to produce a shared sparse index"

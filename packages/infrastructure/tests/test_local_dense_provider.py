import pytest

from regintel_infrastructure.embeddings.local_dense_provider import LocalDenseEmbeddingProvider

# Not Docker-dependent, but downloads real model weights on first run — grouped with
# integration tests so `make test` stays instant and offline-safe.
pytestmark = pytest.mark.integration


async def test_embed_returns_one_vector_per_text_with_expected_dimensions() -> None:
    provider = LocalDenseEmbeddingProvider()

    vectors = await provider.embed(["customer due diligence", "know your customer"])

    assert len(vectors) == 2
    assert all(len(v) == 384 for v in vectors)


async def test_embed_gives_similar_texts_closer_vectors_than_dissimilar_ones() -> None:
    provider = LocalDenseEmbeddingProvider()

    similar_a, similar_b, dissimilar = await provider.embed(
        [
            "Regulated entities shall maintain KYC records for all customers.",
            "Entities must keep know-your-customer documentation for clients.",
            "The weather in Mumbai is expected to be hot this week.",
        ]
    )

    def cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        return dot / (norm_a * norm_b)

    assert cosine_similarity(similar_a, similar_b) > cosine_similarity(similar_a, dissimilar)

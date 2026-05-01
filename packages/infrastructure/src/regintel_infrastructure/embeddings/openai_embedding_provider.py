from openai import AsyncOpenAI


class OpenAIEmbeddingProvider:
    """Implements the application layer's EmbeddingProvider port via OpenAI.

    dimensions shortens text-embedding-3-large's native 3072-dim output (see
    Settings.embedding_dimensions for why) — OpenAI supports this natively via
    Matryoshka representation learning, so it's not a lossy truncation.
    """

    def __init__(self, client: AsyncOpenAI, model: str, dimensions: int) -> None:
        self._client = client
        self._model = model
        self._dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._model, input=texts, dimensions=self._dimensions
        )
        return [item.embedding for item in response.data]

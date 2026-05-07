import asyncio

from fastembed import TextEmbedding


class LocalDenseEmbeddingProvider:
    """Implements the application layer's EmbeddingProvider port with a local
    fastembed model — no API key, no per-call cost, so anyone cloning this repo
    can run ingestion without signing up for anything. Same CPU-bound-to-thread
    pattern as the BM25 sparse provider, since ONNX inference blocks otherwise.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self._model = TextEmbedding(model_name=model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = await asyncio.to_thread(lambda: list(self._model.embed(texts)))
        return [embedding.tolist() for embedding in embeddings]

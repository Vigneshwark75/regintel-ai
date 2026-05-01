import asyncio

from fastembed import SparseTextEmbedding

from regintel_application.ports.vector_store import SparseVector


class Bm25SparseEmbeddingProvider:
    """Implements the application layer's SparseEmbeddingProvider port with a local
    BM25 model (fastembed) — no external API call, so it never rate-limits or costs
    money per query. The model runs CPU-bound ONNX inference, so calls are pushed to
    a thread to avoid blocking the event loop.
    """

    def __init__(self, model_name: str = "Qdrant/bm25") -> None:
        self._model = SparseTextEmbedding(model_name=model_name)

    async def embed_sparse(self, texts: list[str]) -> list[SparseVector]:
        embeddings = await asyncio.to_thread(lambda: list(self._model.embed(texts)))
        return [
            SparseVector(indices=list(embedding.indices), values=list(embedding.values))
            for embedding in embeddings
        ]

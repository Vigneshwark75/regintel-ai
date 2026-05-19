import asyncio

from fastembed.rerank.cross_encoder import TextCrossEncoder

from regintel_application.ports.reranker import RerankedChunk
from regintel_domain import Chunk


class LocalCrossEncoderReranker:
    """Implements the application layer's Reranker port with a local fastembed
    cross-encoder — no API key, same to-thread pattern as the other local models
    since ONNX inference is CPU-bound and would otherwise block the event loop.
    Cohere Rerank remains a viable drop-in adapter behind this same port if
    higher quality is worth the cost later.
    """

    def __init__(self, model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2") -> None:
        self._model = TextCrossEncoder(model_name=model_name)

    async def rerank(self, query: str, chunks: list[Chunk], top_n: int) -> list[RerankedChunk]:
        if not chunks:
            return []

        documents = [chunk.content for chunk in chunks]
        scores = await asyncio.to_thread(lambda: list(self._model.rerank(query, documents)))

        ranked = sorted(zip(chunks, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        return [RerankedChunk(chunk=chunk, score=score) for chunk, score in ranked[:top_n]]

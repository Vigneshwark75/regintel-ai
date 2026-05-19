from dataclasses import dataclass
from typing import Protocol

from regintel_domain import Chunk


@dataclass(frozen=True)
class RerankedChunk:
    chunk: Chunk
    score: float


class Reranker(Protocol):
    """Cross-encoder reranking port — takes the fused dense+sparse candidate set
    and does a precision pass scoring the query against each candidate directly,
    rather than via separately-computed embeddings."""

    async def rerank(self, query: str, chunks: list[Chunk], top_n: int) -> list[RerankedChunk]: ...

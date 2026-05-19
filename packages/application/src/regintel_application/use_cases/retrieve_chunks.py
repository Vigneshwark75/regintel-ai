from dataclasses import dataclass

from regintel_application.ports.document_repository import DocumentRepository
from regintel_application.ports.embedding_provider import EmbeddingProvider, SparseEmbeddingProvider
from regintel_application.ports.reranker import Reranker
from regintel_application.ports.vector_store import VectorStore
from regintel_domain import Citation


@dataclass
class RetrieveChunksUseCase:
    """The retrieve_chunks tool: embed the query (dense + sparse), hybrid-search
    Qdrant (fused via RRF), fetch the candidates' text from Postgres, rerank with
    a cross-encoder, and return grounded Citations ready to hand to an LLM.

    candidate_pool is intentionally larger than top_n — RRF fusion gives a decent
    but not final ranking, so we pull a wider net for the cross-encoder to do a
    real precision pass over before truncating to what's actually returned.
    """

    document_repository: DocumentRepository
    vector_store: VectorStore
    embedding_provider: EmbeddingProvider
    sparse_embedding_provider: SparseEmbeddingProvider
    reranker: Reranker

    async def execute(self, query: str, top_n: int = 5, candidate_pool: int = 20) -> list[Citation]:
        dense_vectors = await self.embedding_provider.embed([query])
        sparse_vectors = await self.sparse_embedding_provider.embed_sparse([query])

        hits = await self.vector_store.search(
            dense_vector=dense_vectors[0], sparse_vector=sparse_vectors[0], limit=candidate_pool
        )
        if not hits:
            return []

        chunks = await self.document_repository.get_chunks_by_ids([hit.chunk_id for hit in hits])
        if not chunks:
            return []

        reranked = await self.reranker.rerank(query, chunks, top_n=top_n)

        return [
            Citation(
                document_id=result.chunk.document_id,
                chunk_id=result.chunk.id,
                quoted_text=result.chunk.content,
                clause_reference=result.chunk.clause_reference,
                page_number=result.chunk.page_number,
            )
            for result in reranked
        ]

from dataclasses import dataclass

from regintel_application.ports.document_repository import DocumentRepository
from regintel_application.ports.embedding_provider import EmbeddingProvider, SparseEmbeddingProvider
from regintel_application.ports.vector_store import VectorEntry, VectorStore
from regintel_domain import Chunk, Document


@dataclass
class IngestDocumentUseCase:
    """Persists a parsed-and-chunked Document, embeds its chunks (dense + sparse),
    and indexes them for retrieval.

    Parsing raw PDF/DOCX bytes into Chunks happens before this use case runs —
    that's format-specific infrastructure concern, not business logic. This use
    case only knows about the ports: repository, vector store, two embedders.
    """

    document_repository: DocumentRepository
    vector_store: VectorStore
    embedding_provider: EmbeddingProvider
    sparse_embedding_provider: SparseEmbeddingProvider

    async def execute(self, document: Document, chunks: list[Chunk]) -> None:
        if not chunks:
            raise ValueError("a document must have at least one chunk to be ingested")

        await self.document_repository.save_document(document)
        await self.document_repository.save_chunks(chunks)

        texts = [chunk.content for chunk in chunks]
        dense_vectors = await self.embedding_provider.embed(texts)
        sparse_vectors = await self.sparse_embedding_provider.embed_sparse(texts)

        entries = [
            VectorEntry(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                dense_vector=dense_vector,
                sparse_vector=sparse_vector,
            )
            for chunk, dense_vector, sparse_vector in zip(
                chunks, dense_vectors, sparse_vectors, strict=True
            )
        ]
        await self.vector_store.upsert_chunks(entries)

from collections.abc import AsyncIterator
from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from qdrant_client import AsyncQdrantClient

from regintel_application.use_cases.ingest_document import IngestDocumentUseCase
from regintel_application.use_cases.retrieve_chunks import RetrieveChunksUseCase
from regintel_domain import Document, DocumentType
from regintel_infrastructure.chunking.regulation_chunker import build_chunks_from_text
from regintel_infrastructure.db.document_repository import PostgresDocumentRepository
from regintel_infrastructure.embeddings.bm25_sparse_provider import Bm25SparseEmbeddingProvider
from regintel_infrastructure.embeddings.local_dense_provider import LocalDenseEmbeddingProvider
from regintel_infrastructure.reranking.local_cross_encoder_reranker import LocalCrossEncoderReranker
from regintel_infrastructure.vector_store.qdrant_store import QdrantVectorStore

pytestmark = pytest.mark.integration

_REGULATION_TEXT = """1. Customer Due Diligence

Regulated entities shall undertake Customer Due Diligence measures while
commencing an account-based relationship, including verification of identity
and address of the customer using officially valid documents.

2. Logistics During Monsoon

The monsoon season typically affects logistics operations across western
India between June and September each year, and branches should plan
courier dispatch schedules accordingly.
"""


@pytest_asyncio.fixture
async def vector_store(qdrant_client: AsyncQdrantClient) -> AsyncIterator[QdrantVectorStore]:
    collection_name = f"test_{uuid4().hex}"
    store = QdrantVectorStore(qdrant_client, collection_name=collection_name, dense_dimensions=384)
    await store.ensure_collection()

    yield store

    await qdrant_client.delete_collection(collection_name)


async def test_ingested_chunk_is_retrievable_by_a_relevant_query(
    db_session, vector_store: QdrantVectorStore  # type: ignore[no-untyped-def]
) -> None:
    document_repository = PostgresDocumentRepository(db_session)
    dense_provider = LocalDenseEmbeddingProvider()
    sparse_provider = Bm25SparseEmbeddingProvider()

    document = Document(
        id=uuid4(),
        title="Master Direction on KYC",
        document_type=DocumentType.MASTER_DIRECTION,
        reference_number="RBI/DBR/2016-17/18",
        issued_date=date(2016, 2, 25),
    )
    chunks = build_chunks_from_text(document.id, _REGULATION_TEXT)

    ingest = IngestDocumentUseCase(
        document_repository=document_repository,
        vector_store=vector_store,
        embedding_provider=dense_provider,
        sparse_embedding_provider=sparse_provider,
    )
    await ingest.execute(document, chunks)

    retrieve = RetrieveChunksUseCase(
        document_repository=document_repository,
        vector_store=vector_store,
        embedding_provider=dense_provider,
        sparse_embedding_provider=sparse_provider,
        reranker=LocalCrossEncoderReranker(),
    )
    citations = await retrieve.execute(
        "What are the customer due diligence requirements for new accounts?", top_n=1
    )

    assert len(citations) == 1
    assert citations[0].document_id == document.id
    assert "due diligence" in citations[0].quoted_text.lower()

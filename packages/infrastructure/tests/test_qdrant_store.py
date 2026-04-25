from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from qdrant_client import AsyncQdrantClient

from regintel_application.ports.vector_store import SparseVector, VectorEntry
from regintel_infrastructure.vector_store.qdrant_store import QdrantVectorStore

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def vector_store(qdrant_client: AsyncQdrantClient) -> AsyncIterator[QdrantVectorStore]:
    collection_name = f"test_{uuid4().hex}"
    store = QdrantVectorStore(qdrant_client, collection_name=collection_name, dense_dimensions=8)
    await store.ensure_collection()

    yield store

    await qdrant_client.delete_collection(collection_name)


async def test_ensure_collection_is_idempotent(vector_store: QdrantVectorStore) -> None:
    await vector_store.ensure_collection()  # should not raise on second call


async def test_upsert_then_search_finds_the_chunk(vector_store: QdrantVectorStore) -> None:
    document_id = uuid4()
    chunk_id = uuid4()
    dense = [0.1] * 8
    sparse = SparseVector(indices=[1, 5], values=[0.5, 0.3])

    await vector_store.upsert_chunks(
        [
            VectorEntry(
                chunk_id=chunk_id,
                document_id=document_id,
                dense_vector=dense,
                sparse_vector=sparse,
            )
        ]
    )

    hits = await vector_store.search(dense_vector=dense, sparse_vector=sparse, limit=5)

    assert any(hit.chunk_id == chunk_id and hit.document_id == document_id for hit in hits)


async def test_delete_by_document_removes_its_chunks(vector_store: QdrantVectorStore) -> None:
    document_id = uuid4()
    chunk_id = uuid4()
    dense = [0.2] * 8
    sparse = SparseVector(indices=[2], values=[0.9])

    await vector_store.upsert_chunks(
        [
            VectorEntry(
                chunk_id=chunk_id,
                document_id=document_id,
                dense_vector=dense,
                sparse_vector=sparse,
            )
        ]
    )

    await vector_store.delete_by_document(document_id)
    hits = await vector_store.search(dense_vector=dense, sparse_vector=sparse, limit=5)

    assert all(hit.chunk_id != chunk_id for hit in hits)

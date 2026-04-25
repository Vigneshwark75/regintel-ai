from uuid import UUID

from qdrant_client import AsyncQdrantClient, models

from regintel_application.ports.vector_store import SearchHit, SparseVector, VectorEntry


class QdrantVectorStore:
    """Implements the application layer's VectorStore port against Qdrant.

    Each chunk is stored with two named vectors — "dense" (OpenAI embeddings)
    and "sparse" (BM25) — in one collection. `search` fuses both result lists
    with Qdrant's native RRF, so callers never see dense/sparse as separate
    concerns.
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        dense_dimensions: int,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._dense_dimensions = dense_dimensions

    async def ensure_collection(self) -> None:
        if await self._client.collection_exists(self._collection_name):
            return

        await self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=self._dense_dimensions, distance=models.Distance.COSINE
                ),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(),
            },
        )

    async def upsert_chunks(self, entries: list[VectorEntry]) -> None:
        points = [
            models.PointStruct(
                id=str(entry.chunk_id),
                vector={
                    "dense": entry.dense_vector,
                    "sparse": models.SparseVector(
                        indices=entry.sparse_vector.indices,
                        values=entry.sparse_vector.values,
                    ),
                },
                payload={"document_id": str(entry.document_id)},
            )
            for entry in entries
        ]
        await self._client.upsert(collection_name=self._collection_name, points=points)

    async def search(
        self, dense_vector: list[float], sparse_vector: SparseVector, limit: int = 10
    ) -> list[SearchHit]:
        result = await self._client.query_points(
            collection_name=self._collection_name,
            prefetch=[
                models.Prefetch(query=dense_vector, using="dense", limit=limit * 2),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_vector.indices, values=sparse_vector.values
                    ),
                    using="sparse",
                    limit=limit * 2,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )

        hits = []
        for point in result.points:
            assert point.payload is not None, "points upserted here always carry a payload"
            hits.append(
                SearchHit(
                    chunk_id=UUID(str(point.id)),
                    document_id=UUID(str(point.payload["document_id"])),
                    score=point.score,
                )
            )
        return hits

    async def delete_by_document(self, document_id: UUID) -> None:
        await self._client.delete(
            collection_name=self._collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from groq import AsyncGroq
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from regintel_application.agent.orchestrator import ComplianceAgent
from regintel_application.use_cases.compare_regulations import CompareRegulationsUseCase
from regintel_application.use_cases.generate_action_items import GenerateActionItemsUseCase
from regintel_application.use_cases.ingest_document import IngestDocumentUseCase
from regintel_application.use_cases.retrieve_chunks import RetrieveChunksUseCase
from regintel_application.use_cases.summarize_regulation import SummarizeRegulationUseCase
from regintel_infrastructure.db.base import create_engine, create_session_factory, session_scope
from regintel_infrastructure.db.document_repository import PostgresDocumentRepository
from regintel_infrastructure.embeddings.bm25_sparse_provider import Bm25SparseEmbeddingProvider
from regintel_infrastructure.embeddings.local_dense_provider import LocalDenseEmbeddingProvider
from regintel_infrastructure.guardrails.nemo_guardrails_service import NeMoGuardrailsService
from regintel_infrastructure.llm.groq_provider import GroqProvider
from regintel_infrastructure.reranking.local_cross_encoder_reranker import LocalCrossEncoderReranker
from regintel_infrastructure.vector_store.qdrant_store import QdrantVectorStore
from regintel_shared.config import get_settings

# Everything below is process-lifetime: DB engine/pool, Qdrant client, Groq client, and
# the local model-backed providers all carry real setup cost (connection pools, loaded
# ONNX models) that must not be repeated per request. @lru_cache makes each a singleton;
# only the DB session (below) is created fresh per request, as sessions must be.


@lru_cache
def get_engine() -> AsyncEngine:
    return create_engine(get_settings().postgres_dsn)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return create_session_factory(get_engine())


async def get_db_session() -> AsyncIterator[AsyncSession]:
    # Reuses the same session_scope() helper Phase 2's integration tests rely on —
    # commits on a clean request, rolls back on an exception. An earlier version of
    # this dependency opened a plain `async with session_factory() as session` with
    # no commit at all, which meant every write silently rolled back on session
    # close: Qdrant would show the new vector (unconditional write) while Postgres
    # showed nothing. Caught via a real end-to-end test, not a mock.
    async with session_scope(get_session_factory()) as session:
        yield session


@lru_cache
def get_qdrant_client() -> AsyncQdrantClient:
    settings = get_settings()
    return AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def get_vector_store() -> QdrantVectorStore:
    settings = get_settings()
    return QdrantVectorStore(
        get_qdrant_client(),
        collection_name=settings.qdrant_collection,
        dense_dimensions=settings.embedding_dimensions,
    )


@lru_cache
def get_dense_embedding_provider() -> LocalDenseEmbeddingProvider:
    return LocalDenseEmbeddingProvider(model_name=get_settings().embedding_model)


@lru_cache
def get_sparse_embedding_provider() -> Bm25SparseEmbeddingProvider:
    return Bm25SparseEmbeddingProvider()


@lru_cache
def get_reranker() -> LocalCrossEncoderReranker:
    return LocalCrossEncoderReranker()


@lru_cache
def get_groq_client() -> AsyncGroq:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured — see .env.example")
    return AsyncGroq(api_key=settings.groq_api_key)


@lru_cache
def get_llm_provider() -> GroqProvider:
    return GroqProvider(client=get_groq_client(), model=get_settings().llm_model)


@lru_cache
def get_guardrails() -> NeMoGuardrailsService:
    return NeMoGuardrailsService()


def get_document_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PostgresDocumentRepository:
    return PostgresDocumentRepository(session)


def get_ingest_document_use_case(
    document_repository: Annotated[PostgresDocumentRepository, Depends(get_document_repository)],
) -> IngestDocumentUseCase:
    return IngestDocumentUseCase(
        document_repository=document_repository,
        vector_store=get_vector_store(),
        embedding_provider=get_dense_embedding_provider(),
        sparse_embedding_provider=get_sparse_embedding_provider(),
        guardrails=get_guardrails(),
    )


def get_retrieve_chunks_use_case(
    document_repository: Annotated[PostgresDocumentRepository, Depends(get_document_repository)],
) -> RetrieveChunksUseCase:
    return RetrieveChunksUseCase(
        document_repository=document_repository,
        vector_store=get_vector_store(),
        embedding_provider=get_dense_embedding_provider(),
        sparse_embedding_provider=get_sparse_embedding_provider(),
        reranker=get_reranker(),
    )


def get_summarize_regulation_use_case(
    document_repository: Annotated[PostgresDocumentRepository, Depends(get_document_repository)],
) -> SummarizeRegulationUseCase:
    return SummarizeRegulationUseCase(
        document_repository=document_repository, llm_provider=get_llm_provider()
    )


def get_compare_regulations_use_case(
    document_repository: Annotated[PostgresDocumentRepository, Depends(get_document_repository)],
) -> CompareRegulationsUseCase:
    return CompareRegulationsUseCase(
        document_repository=document_repository, llm_provider=get_llm_provider()
    )


def get_generate_action_items_use_case(
    retrieve_chunks: Annotated[RetrieveChunksUseCase, Depends(get_retrieve_chunks_use_case)],
) -> GenerateActionItemsUseCase:
    return GenerateActionItemsUseCase(
        retrieve_chunks=retrieve_chunks, llm_provider=get_llm_provider()
    )


def get_compliance_agent(
    retrieve_chunks: Annotated[RetrieveChunksUseCase, Depends(get_retrieve_chunks_use_case)],
    summarize_regulation: Annotated[
        SummarizeRegulationUseCase, Depends(get_summarize_regulation_use_case)
    ],
    compare_regulations: Annotated[
        CompareRegulationsUseCase, Depends(get_compare_regulations_use_case)
    ],
    generate_action_items: Annotated[
        GenerateActionItemsUseCase, Depends(get_generate_action_items_use_case)
    ],
) -> ComplianceAgent:
    return ComplianceAgent(
        llm_provider=get_llm_provider(),
        retrieve_chunks=retrieve_chunks,
        summarize_regulation=summarize_regulation,
        compare_regulations=compare_regulations,
        generate_action_items=generate_action_items,
        guardrails=get_guardrails(),
    )

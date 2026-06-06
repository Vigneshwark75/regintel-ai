from collections.abc import AsyncIterator
from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from qdrant_client import AsyncQdrantClient

from regintel_application.agent.orchestrator import ComplianceAgent
from regintel_application.use_cases.compare_regulations import CompareRegulationsUseCase
from regintel_application.use_cases.generate_action_items import GenerateActionItemsUseCase
from regintel_application.use_cases.ingest_document import IngestDocumentUseCase
from regintel_application.use_cases.retrieve_chunks import RetrieveChunksUseCase
from regintel_application.use_cases.summarize_regulation import SummarizeRegulationUseCase
from regintel_domain import Document, DocumentType
from regintel_infrastructure.chunking.regulation_chunker import build_chunks_from_text
from regintel_infrastructure.db.document_repository import PostgresDocumentRepository
from regintel_infrastructure.embeddings.bm25_sparse_provider import Bm25SparseEmbeddingProvider
from regintel_infrastructure.embeddings.local_dense_provider import LocalDenseEmbeddingProvider
from regintel_infrastructure.guardrails.nemo_guardrails_service import NeMoGuardrailsService
from regintel_infrastructure.llm.groq_provider import GroqProvider
from regintel_infrastructure.reranking.local_cross_encoder_reranker import LocalCrossEncoderReranker
from regintel_infrastructure.vector_store.qdrant_store import QdrantVectorStore

pytestmark = pytest.mark.integration

_REGULATION_TEXT = """1. Customer Due Diligence

Regulated entities shall undertake Customer Due Diligence measures while
commencing an account-based relationship, including verification of identity
and address of the customer using officially valid documents. Entities must
retain these records for a minimum of five years from the date of the
transaction or the end of the relationship, whichever is later.
"""


@pytest_asyncio.fixture
async def vector_store(qdrant_client: AsyncQdrantClient) -> AsyncIterator[QdrantVectorStore]:
    collection_name = f"test_{uuid4().hex}"
    store = QdrantVectorStore(qdrant_client, collection_name=collection_name, dense_dimensions=384)
    await store.ensure_collection()

    yield store

    await qdrant_client.delete_collection(collection_name)


async def test_agent_answers_a_grounded_question_after_ingestion(
    db_session,  # type: ignore[no-untyped-def]
    vector_store: QdrantVectorStore,
    groq_provider: GroqProvider,
    guardrails: NeMoGuardrailsService,
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
        guardrails=guardrails,
    )
    await ingest.execute(document, chunks)

    retrieve_chunks = RetrieveChunksUseCase(
        document_repository=document_repository,
        vector_store=vector_store,
        embedding_provider=dense_provider,
        sparse_embedding_provider=sparse_provider,
        reranker=LocalCrossEncoderReranker(),
    )
    agent = ComplianceAgent(
        llm_provider=groq_provider,
        retrieve_chunks=retrieve_chunks,
        summarize_regulation=SummarizeRegulationUseCase(
            document_repository=document_repository, llm_provider=groq_provider
        ),
        compare_regulations=CompareRegulationsUseCase(
            document_repository=document_repository, llm_provider=groq_provider
        ),
        generate_action_items=GenerateActionItemsUseCase(
            retrieve_chunks=retrieve_chunks, llm_provider=groq_provider
        ),
        guardrails=guardrails,
    )

    answer, citations = await agent.ask("How long must customer due diligence records be retained?")

    assert "five" in answer.lower() or "5" in answer
    assert len(citations) > 0
    assert any(c.document_id == document.id for c in citations)

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from groq import AsyncGroq
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from regintel_infrastructure.db.base import create_engine, create_session_factory
from regintel_infrastructure.guardrails.nemo_guardrails_service import NeMoGuardrailsService
from regintel_infrastructure.llm.groq_provider import GroqProvider
from regintel_shared.asyncio_compat import ensure_windows_selector_event_loop
from regintel_shared.config import get_settings

ensure_windows_selector_event_loop()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    engine = create_engine(settings.postgres_dsn)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def qdrant_client() -> AsyncIterator[AsyncQdrantClient]:
    settings = get_settings()
    client = AsyncQdrantClient(url=settings.qdrant_url)

    yield client

    await client.close()


@pytest_asyncio.fixture
async def groq_provider() -> AsyncIterator[GroqProvider]:
    settings = get_settings()
    assert settings.groq_api_key, "GROQ_API_KEY must be set in .env to run Groq integration tests"
    client = AsyncGroq(api_key=settings.groq_api_key)

    yield GroqProvider(client=client, model=settings.llm_model)

    await client.close()


@pytest.fixture
def guardrails() -> NeMoGuardrailsService:
    return NeMoGuardrailsService()

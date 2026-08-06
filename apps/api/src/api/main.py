import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from regintel_shared.asyncio_compat import ensure_windows_selector_event_loop
from regintel_shared.config import get_settings
from regintel_shared.logging import configure_logging, get_logger

# Must run before uvicorn creates its event loop, regardless of whether this
# module is launched via `python -m`, the uvicorn CLI, or programmatically.
ensure_windows_selector_event_loop()

from api.dependencies import (  # noqa: E402 -- must follow the event loop fix above
    get_dense_embedding_provider,
    get_guardrails,
    get_reranker,
    get_sparse_embedding_provider,
    get_vector_store,
)
from api.routers import agent, auth, documents  # noqa: E402
from regintel_infrastructure.observability import configure_opik_tracing  # noqa: E402

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)
configure_opik_tracing(settings.opik_api_key, settings.opik_workspace, settings.opik_project_name)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await get_vector_store().ensure_collection()
    # These are @lru_cache'd in dependencies.py, so this is what actually
    # constructs them (downloading + loading the local ONNX models, parsing the
    # Guardrails config) — done once here at boot, where a slow cold load just
    # delays "ready", instead of on whichever request happens to be first, where
    # the same delay reads as that request hanging or hitting a proxy timeout.
    await asyncio.to_thread(get_dense_embedding_provider)
    await asyncio.to_thread(get_sparse_embedding_provider)
    await asyncio.to_thread(get_reranker)
    await asyncio.to_thread(get_guardrails)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="RegIntel AI",
        description="Enterprise Regulatory Intelligence Platform — Agentic RAG API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(agent.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    logger.info("starting_api", host=settings.api_host, port=settings.api_port)
    uvicorn.run("api.main:app", host=settings.api_host, port=settings.api_port, reload=True)

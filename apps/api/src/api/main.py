from fastapi import FastAPI

from regintel_shared.asyncio_compat import ensure_windows_selector_event_loop
from regintel_shared.config import get_settings
from regintel_shared.logging import configure_logging, get_logger

# Must run before uvicorn creates its event loop, regardless of whether this
# module is launched via `python -m`, the uvicorn CLI, or programmatically.
ensure_windows_selector_event_loop()

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="RegIntel AI",
        description="Enterprise Regulatory Intelligence Platform — Agentic RAG API",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    logger.info("starting_api", host=settings.api_host, port=settings.api_port)
    uvicorn.run("api.main:app", host=settings.api_host, port=settings.api_port, reload=True)

from fastapi import FastAPI

from regintel_shared.config import get_settings
from regintel_shared.logging import configure_logging, get_logger

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

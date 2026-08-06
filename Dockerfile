# Builds the FastAPI backend (apps/api). Built from the repo root because this is a
# uv workspace — uv needs every member's pyproject.toml present to resolve dependency
# graphs, even though only the regintel-api package (and its transitive workspace
# deps: domain, application, infrastructure, shared) actually gets installed.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY . .

RUN uv sync --frozen --package regintel-api

EXPOSE 8000

# Applies pending Alembic migrations, then starts the API. Runs on every boot rather
# than as a separate release step so this works on hosts (like Render's free tier)
# that don't support a pre-deploy/release-phase command — `alembic upgrade head` is a
# no-op when there's nothing new to apply, so this is safe to repeat on every restart.
# $PORT is set by the hosting platform (e.g. Render); 8000 is the local-dev fallback.
CMD ["sh", "-c", "cd packages/infrastructure && uv run --project ../.. --package regintel-infrastructure alembic upgrade head && cd /app && uv run --package regintel-api uvicorn api.main:app --app-dir apps/api/src --host 0.0.0.0 --port ${PORT:-8000}"]

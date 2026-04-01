.PHONY: sync lint format typecheck test run-api run-ui infra-up infra-down

sync:
	uv sync --all-packages

lint:
	uv run ruff check .

format:
	uv run black .
	uv run ruff check --fix .

typecheck:
	uv run mypy packages apps

test:
	uv run pytest

run-api:
	uv run --package regintel-api uvicorn api.main:app --app-dir apps/api/src --reload

run-ui:
	uv run --package regintel-ui streamlit run apps/ui/src/ui/app.py

infra-up:
	docker compose -f deployment/docker-compose.yml up -d

infra-down:
	docker compose -f deployment/docker-compose.yml down

from datetime import UTC, datetime
from uuid import uuid4

from api.dependencies import get_compliance_agent, get_generate_action_items_use_case
from api.main import app
from fastapi.testclient import TestClient

from regintel_domain import ActionItem, ActionItemPriority, Citation, UserRole

client = TestClient(app)


class FakeComplianceAgent:
    async def ask(self, question: str) -> tuple[str, list[Citation]]:
        citation = Citation(document_id=uuid4(), chunk_id=uuid4(), quoted_text="relevant clause")
        return f"Answer to: {question}", [citation]


class FakeGenerateActionItemsUseCase:
    async def execute(self, topic: str, owner_role: UserRole) -> list[ActionItem]:
        citation = Citation(document_id=uuid4(), chunk_id=uuid4(), quoted_text="relevant clause")
        return [
            ActionItem(
                id=uuid4(),
                description=f"Do something about {topic}",
                citations=[citation],
                owner_role=owner_role,
                priority=ActionItemPriority.MEDIUM,
                created_at=datetime.now(UTC),
            )
        ]


def _get_token(username: str, password: str) -> str:
    response = client.post("/auth/token", data={"username": username, "password": password})
    return str(response.json()["access_token"])


def test_ask_requires_authentication() -> None:
    response = client.post("/ask", json={"question": "What is KYC?"})

    assert response.status_code == 401


def test_ask_returns_answer_and_citations_for_any_authenticated_role() -> None:
    app.dependency_overrides[get_compliance_agent] = lambda: FakeComplianceAgent()
    try:
        token = _get_token("auditor", "auditor-demo-password")

        response = client.post(
            "/ask",
            json={"question": "What is KYC?"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Answer to: What is KYC?"
        assert len(body["citations"]) == 1
    finally:
        app.dependency_overrides.pop(get_compliance_agent, None)


def test_generate_action_items_returns_items_grounded_in_citations() -> None:
    app.dependency_overrides[get_generate_action_items_use_case] = (
        lambda: FakeGenerateActionItemsUseCase()
    )
    try:
        token = _get_token("ops", "ops-demo-password")

        response = client.post(
            "/action-items",
            json={"topic": "KYC updates", "owner_role": "ops"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        items = response.json()["action_items"]
        assert len(items) == 1
        assert items[0]["owner_role"] == "ops"
        assert len(items[0]["citations"]) == 1
    finally:
        app.dependency_overrides.pop(get_generate_action_items_use_case, None)

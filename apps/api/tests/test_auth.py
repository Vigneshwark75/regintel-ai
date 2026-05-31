import jwt
from api.main import app
from fastapi.testclient import TestClient

from regintel_shared.config import get_settings

client = TestClient(app)


def test_login_with_valid_credentials_returns_a_bearer_token() -> None:
    response = client.post(
        "/auth/token", data={"username": "compliance", "password": "compliance-demo-password"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_issued_token_decodes_to_the_correct_role() -> None:
    response = client.post("/auth/token", data={"username": "cro", "password": "cro-demo-password"})

    settings = get_settings()
    payload = jwt.decode(
        response.json()["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )

    assert payload["sub"] == "cro"
    assert payload["role"] == "cro"


def test_login_with_wrong_password_is_rejected() -> None:
    response = client.post("/auth/token", data={"username": "compliance", "password": "wrong"})

    assert response.status_code == 401


def test_login_with_unknown_username_is_rejected() -> None:
    response = client.post("/auth/token", data={"username": "nobody", "password": "irrelevant"})

    assert response.status_code == 401


def test_protected_endpoint_rejects_a_missing_token() -> None:
    response = client.post("/ask", json={"question": "hello"})

    assert response.status_code == 401


def test_protected_endpoint_rejects_a_garbage_token() -> None:
    response = client.post(
        "/ask", json={"question": "hello"}, headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401

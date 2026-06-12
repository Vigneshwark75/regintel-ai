from datetime import date

import httpx
import pytest
from ui import api_client


@pytest.fixture(autouse=True)
def _session_state(monkeypatch: pytest.MonkeyPatch) -> None:
    # api_client reads st.session_state for the auth token; outside a real Streamlit
    # run there is no session, so stub in a plain dict.
    import streamlit as st

    monkeypatch.setattr(st, "session_state", {"access_token": "test-token"}, raising=False)


def _install_mock_transport(monkeypatch: pytest.MonkeyPatch, handler) -> None:  # type: ignore[no-untyped-def]
    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        request = httpx.Request("POST", url)
        response = handler(request, kwargs)
        response.request = request  # raise_for_status() requires this to be set
        return response

    monkeypatch.setattr(httpx, "post", fake_post)


def test_login_returns_token_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request, kwargs: dict) -> httpx.Response:  # type: ignore[type-arg]
        assert request.url.path == "/auth/token"
        assert kwargs["data"] == {"username": "compliance", "password": "secret"}
        return httpx.Response(200, json={"access_token": "abc123", "token_type": "bearer"})

    _install_mock_transport(monkeypatch, handler)

    token = api_client.login("compliance", "secret")

    assert token == "abc123"


def test_login_returns_none_on_401(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request, kwargs: dict) -> httpx.Response:  # type: ignore[type-arg]
        return httpx.Response(401, json={"detail": "Incorrect username or password"})

    _install_mock_transport(monkeypatch, handler)

    assert api_client.login("compliance", "wrong") is None


def test_ask_sends_bearer_token_and_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request, kwargs: dict) -> httpx.Response:  # type: ignore[type-arg]
        assert request.url.path == "/ask"
        assert kwargs["headers"] == {"Authorization": "Bearer test-token"}
        assert kwargs["json"] == {"question": "What is KYC?"}
        return httpx.Response(200, json={"answer": "It's...", "citations": []})

    _install_mock_transport(monkeypatch, handler)

    result = api_client.ask("What is KYC?")

    assert result["answer"] == "It's..."


def test_upload_document_sends_multipart_form(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request, kwargs: dict) -> httpx.Response:  # type: ignore[type-arg]
        assert request.url.path == "/documents"
        assert kwargs["files"] == {"file": ("kyc.docx", b"fake bytes")}
        assert kwargs["data"]["issued_date"] == "2016-02-25"
        return httpx.Response(
            201, json={"document_id": "11111111-1111-1111-1111-111111111111", "chunk_count": 3}
        )

    _install_mock_transport(monkeypatch, handler)

    result = api_client.upload_document(
        "kyc.docx",
        b"fake bytes",
        "Master Direction on KYC",
        "master_direction",
        "RBI/DBR/2016-17/18",
        date(2016, 2, 25),
    )

    assert result["chunk_count"] == 3


def test_ask_raises_for_a_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request, kwargs: dict) -> httpx.Response:  # type: ignore[type-arg]
        return httpx.Response(500, json={"detail": "boom"})

    _install_mock_transport(monkeypatch, handler)

    with pytest.raises(httpx.HTTPStatusError):
        api_client.ask("What is KYC?")

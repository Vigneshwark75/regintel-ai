from datetime import date
from typing import Any

import httpx
import streamlit as st

from regintel_shared.config import get_settings


def _base_url() -> str:
    return get_settings().ui_api_base_url


def login(username: str, password: str) -> str | None:
    response = httpx.post(
        f"{_base_url()}/auth/token",
        data={"username": username, "password": password},
        timeout=30,
    )
    if response.status_code != 200:
        return None
    token: str = response.json()["access_token"]
    return token


def _auth_headers() -> dict[str, str]:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def upload_document(
    file_name: str,
    file_bytes: bytes,
    title: str,
    document_type: str,
    reference_number: str,
    issued_date: date,
) -> dict[str, Any]:
    response = httpx.post(
        f"{_base_url()}/documents",
        headers=_auth_headers(),
        files={"file": (file_name, file_bytes)},
        data={
            "title": title,
            "document_type": document_type,
            "reference_number": reference_number,
            "issued_date": issued_date.isoformat(),
        },
        timeout=120,
    )
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result


def ask(question: str) -> dict[str, Any]:
    response = httpx.post(
        f"{_base_url()}/ask", headers=_auth_headers(), json={"question": question}, timeout=120
    )
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result


def summarize_document(document_id: str) -> dict[str, Any]:
    response = httpx.post(
        f"{_base_url()}/documents/{document_id}/summarize",
        headers=_auth_headers(),
        timeout=120,
    )
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result


def compare_documents(document_id_a: str, document_id_b: str) -> dict[str, Any]:
    response = httpx.post(
        f"{_base_url()}/documents/compare",
        headers=_auth_headers(),
        json={"document_id_a": document_id_a, "document_id_b": document_id_b},
        timeout=120,
    )
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result


def generate_action_items(topic: str, owner_role: str) -> dict[str, Any]:
    response = httpx.post(
        f"{_base_url()}/action-items",
        headers=_auth_headers(),
        json={"topic": topic, "owner_role": owner_role},
        timeout=120,
    )
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result

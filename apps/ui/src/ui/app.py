import httpx
import streamlit as st

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="RegIntel AI", page_icon=":bank:", layout="wide")

st.title("RegIntel AI")
st.caption("Enterprise Regulatory Intelligence Platform — Agentic RAG")

st.divider()
st.subheader("Backend status")

try:
    response = httpx.get(f"{API_BASE_URL}/health", timeout=3.0)
    response.raise_for_status()
    st.success(f"API reachable: {response.json()}")
except httpx.HTTPError as exc:
    st.error(f"API unreachable at {API_BASE_URL} — start it with `make run-api`. ({exc})")

st.divider()
st.info(
    "Document upload, chat, comparison, and action-item views land in later phases. "
    "This page currently just confirms the API and UI are wired together."
)

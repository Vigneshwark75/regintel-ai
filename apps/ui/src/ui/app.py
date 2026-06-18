import httpx
import streamlit as st

from ui.api_client import (
    ask,
    compare_documents,
    generate_action_items,
    login,
    upload_document,
)

st.set_page_config(page_title="RegIntel AI", page_icon=":bank:", layout="wide")

_DEMO_USERS_HINT = (
    "Demo users: cro/cro-demo-password, compliance/compliance-demo-password, "
    "risk/risk-demo-password, auditor/auditor-demo-password, ops/ops-demo-password"
)

_DOCUMENT_TYPES = ["circular", "master_direction", "notification", "faq", "guideline"]
_ROLES = ["cro", "compliance_officer", "risk", "auditor", "ops"]


def render_login() -> None:
    st.title("RegIntel AI")
    st.caption("Enterprise Regulatory Intelligence Platform — Agentic RAG")

    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        try:
            token = login(username, password)
        except httpx.TransportError:
            st.error(
                "Can't reach the API right now. If you're viewing a hosted demo, the "
                "backend may not be deployed yet — this UI still works standalone, but "
                "needs a running API to log in."
            )
            return
        if token is None:
            st.error("Invalid username or password.")
        else:
            st.session_state["access_token"] = token
            st.session_state["username"] = username
            st.rerun()

    st.info(_DEMO_USERS_HINT)


def render_upload() -> None:
    st.header("Upload a regulatory document")
    with st.form("upload"):
        file = st.file_uploader("Document", type=["pdf", "docx"])
        title = st.text_input("Title")
        document_type = st.selectbox("Document type", _DOCUMENT_TYPES)
        reference_number = st.text_input("Reference number")
        issued_date = st.date_input("Issued date")
        submitted = st.form_submit_button("Upload")

    if not submitted:
        return
    if file is None or not title or not reference_number:
        st.error("File, title, and reference number are required.")
        return

    try:
        result = upload_document(
            file.name, file.getvalue(), title, document_type, reference_number, issued_date
        )
    except httpx.HTTPStatusError as exc:
        st.error(f"Upload failed: {exc.response.text}")
        return

    st.success(f"Ingested {result['chunk_count']} chunk(s). Document ID: `{result['document_id']}`")


def render_ask() -> None:
    st.header("Ask a compliance question")
    question = st.text_area("Question")

    if not (st.button("Ask") and question):
        return

    with st.spinner("Thinking..."):
        try:
            result = ask(question)
        except httpx.HTTPStatusError as exc:
            st.error(f"Request failed: {exc.response.text}")
            return

    st.markdown(f"**Answer:** {result['answer']}")
    citations = result["citations"]
    if not citations:
        st.caption("No citations returned.")
        return

    st.subheader("Citations")
    for citation in citations:
        label = citation.get("clause_reference") or citation["chunk_id"]
        with st.expander(f"Clause {label}"):
            st.write(citation["quoted_text"])


def render_compare() -> None:
    st.header("Compare two regulations")
    st.caption("Paste the document IDs returned from the Upload page.")
    col1, col2 = st.columns(2)
    document_id_a = col1.text_input("Document ID A")
    document_id_b = col2.text_input("Document ID B")

    if not (st.button("Compare") and document_id_a and document_id_b):
        return

    with st.spinner("Comparing..."):
        try:
            result = compare_documents(document_id_a, document_id_b)
        except httpx.HTTPStatusError as exc:
            st.error(f"Comparison failed: {exc.response.text}")
            return

    st.write(result["comparison"])


def render_action_items() -> None:
    st.header("Generate compliance action items")
    topic = st.text_input("Topic")
    owner_role = st.selectbox("Owner role", _ROLES)

    if not (st.button("Generate") and topic):
        return

    with st.spinner("Generating..."):
        try:
            result = generate_action_items(topic, owner_role)
        except httpx.HTTPStatusError as exc:
            st.error(f"Generation failed: {exc.response.text}")
            return

    items = result["action_items"]
    if not items:
        st.info("No grounded action items could be generated for that topic.")
        return

    for item in items:
        with st.container(border=True):
            st.markdown(f"**[{item['priority'].upper()}]** {item['description']}")
            st.caption(f"Owner: {item['owner_role']} · Status: {item['status']}")
            for citation in item["citations"]:
                st.markdown(f"> {citation['quoted_text']}")


def render_app() -> None:
    st.sidebar.title("RegIntel AI")
    st.sidebar.caption(f"Logged in as {st.session_state.get('username')}")
    if st.sidebar.button("Log out"):
        st.session_state.clear()
        st.rerun()

    page = st.sidebar.radio("Navigate", ["Ask", "Upload", "Compare", "Action Items"])
    if page == "Ask":
        render_ask()
    elif page == "Upload":
        render_upload()
    elif page == "Compare":
        render_compare()
    elif page == "Action Items":
        render_action_items()


if "access_token" not in st.session_state:
    render_login()
else:
    render_app()

# RegIntel AI

**Enterprise Regulatory Intelligence Platform — Agentic RAG**

Banks and NBFCs receive a constant stream of RBI circulars, master directions, notifications,
and FAQs. Compliance teams (CRO, Compliance Officers, Risk, Internal Audit, Ops) spend
significant time reading these documents, spotting what changed, answering regulatory
questions, and figuring out business impact.

RegIntel AI is not a "chat with PDF" demo. It's an agentic RAG platform: documents are
ingested into a retrieval system, and an LLM-driven agent uses tools to answer questions with
grounded citations, compare regulation versions, summarize documents, and generate compliance
action items — the same tasks a compliance analyst does today, faster and auditable.

## Why agentic, not just RAG

A plain RAG pipeline retrieves chunks and asks an LLM to answer. That's enough for "what does
this circular say." It's not enough for "what changed between the March and June master
directions, and what do we need to do about it" — that requires the system to decide *which*
tool to use (retrieve vs. compare vs. summarize), potentially chain several, and ground every
claim back to a source clause. That decision-making loop is the "agentic" part.

## Architecture

Hexagonal / clean architecture: domain logic has zero knowledge of Qdrant, Postgres, or which
LLM vendor is active. This is what makes "swap the LLM provider" or "swap the vector store" a
contained change instead of a rewrite.

```
regintel-ai/
├── apps/
│   ├── api/              FastAPI — HTTP layer, auth, request/response schemas
│   └── ui/                Streamlit — upload, chat, comparison, action-item dashboards
├── packages/
│   ├── domain/             Entities & value objects (Document, Chunk, RegulationVersion,
│   │                       ActionItem, ComplianceQuery) — pure Python, no I/O
│   ├── application/         Use cases (IngestDocument, AskQuestion, CompareRegulations,
│   │                       GenerateActionItems, SummarizeRegulation) + ports (interfaces):
│   │                       LLMProvider, VectorStore, DocumentRepository, EmbeddingProvider
│   ├── infrastructure/      Adapters implementing those ports: AnthropicProvider,
│   │                       OpenAIProvider, QdrantVectorStore, PostgresDocumentRepository,
│   │                       PDF/DOCX parsers, regulation-aware chunker
│   └── shared/               Config, logging, exceptions — the shared kernel
├── deployment/              Docker Compose (Postgres, Qdrant, and later the apps)
└── tests/
```

**Two core flows:**

1. **Ingestion** — upload PDF/DOCX → parse → chunk (clause/section-aware) → embed
   (OpenAI `text-embedding-3-large`) → vectors into Qdrant, metadata + full text into Postgres.
2. **Agentic query** — user asks a question → a LangGraph agent runs a tool-calling loop against
   the active LLM provider, choosing from `retrieve_chunks`, `compare_regulations`,
   `generate_action_items`, `summarize_regulation` → every claim is grounded in retrieved
   chunks and cited back to its source clause/page.

**Retrieval (`retrieve_chunks`)** — dense (OpenAI embeddings) and sparse (BM25, via a
`fastembed` sparse vector in the same Qdrant collection) search run together and are fused with
Qdrant's native RRF, then the fused candidates are reranked with Cohere Rerank (a cross-encoder)
for a final precision pass. Deliberately *not* included yet: HyDE (hypothetical-document query
expansion) — dense+sparse+RRF+rerank is already a strong baseline, and HyDE adds an LLM call
(cost + latency) to every query. It's a candidate to add later, driven by what the Phase 9
Ragas evals show is actually missing, not added speculatively now.

**Multi-provider LLM layer** — one `LLMProvider` port, `AnthropicProvider` and `OpenAIProvider`
adapters behind it, selected via config with a fallback chain. The point isn't "support two
SDKs," it's a system that keeps working if one vendor is rate-limited or down.

**Guardrails** — NeMo Guardrails around both directions: ingested documents are screened for
prompt-injection patterns before they ever reach the LLM context, and agent outputs are
validated against structured schemas before being returned to a user.

**Observability & evals** — every LLM call and agent step is traced in Opik (also used for
prompt versioning, so a prompt change is never a silent, untracked edit). Retrieval and answer
quality are measured with Ragas (faithfulness, context precision/recall, answer relevancy)
against a small golden eval set.

**Auth/RBAC** — JWT-based, roles: CRO, Compliance Officer, Risk, Auditor, Ops.

**Memory** — no separate memory store. Every `ComplianceQuery` is persisted in Postgres as it's
answered, which doubles as both short-term conversation context and the audit trail a
compliance system needs to keep regardless.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Frontend | Streamlit |
| Vector store | Qdrant |
| Relational store | PostgreSQL |
| LLM | Anthropic Claude + OpenAI, behind a shared provider abstraction |
| Embeddings | OpenAI `text-embedding-3-large` |
| Reranker | Cohere Rerank |
| Agent orchestration | LangGraph |
| Guardrails | NeMo Guardrails (input injection screening + output validation) |
| Observability & prompt management | Opik |
| Evals | Ragas (faithfulness, context precision/recall, answer relevancy) |
| Memory | Postgres-backed query history (doubles as audit trail) |
| Package/workspace management | uv |
| Tooling | ruff, black, mypy (strict), pytest, pre-commit |

## Getting started

```bash
# Install dependencies for every workspace package
make sync

# Start Postgres + Qdrant
make infra-up

# Apply database migrations
make migrate

# In separate terminals
make run-api   # http://localhost:8000
make run-ui    # http://localhost:8501
```

Copy `.env.example` to `.env` and fill in API keys before Phase 4 (LLM integration) lands.

## Development

```bash
make lint               # ruff
make format               # black + ruff --fix
make typecheck             # mypy --strict
make test                   # pytest, excluding integration tests
make test-integration        # pytest, integration only — needs `make infra-up` first
```

Integration tests (`packages/infrastructure/tests/`) run against the real Postgres/Qdrant
containers rather than mocks — a schema or query-shape bug should fail here, not in
production. They're marked `@pytest.mark.integration` and excluded from the default `make
test` run so the fast feedback loop never needs Docker running.

## Roadmap

Built incrementally, one phase per commit/PR — see commit history for progress.

- [x] **Phase 0** — Repo scaffold: uv workspace, tooling, Docker Compose skeleton
- [x] **Phase 1** — Domain layer: entities, value objects, unit tests
- [x] **Phase 2** — Infrastructure: Postgres models + Alembic, Qdrant client wrapper
- [ ] **Phase 3** — Document ingestion pipeline: parsing, chunking, OpenAI embeddings,
      NeMo Guardrails input screening
- [ ] **Phase 4** — LLM provider abstraction (Anthropic + OpenAI, fallback router)
- [ ] **Phase 5** — Retrieval: dense + BM25 sparse search fused with RRF, Cohere Rerank,
      citation grounding (HyDE deliberately deferred — see Architecture)
- [ ] **Phase 6** — Agent orchestrator: LangGraph tool-calling loop
- [ ] **Phase 7** — FastAPI endpoints + JWT auth/RBAC + NeMo Guardrails output validation
- [ ] **Phase 8** — Streamlit UI: upload, chat, comparison, action-item dashboard
- [ ] **Phase 9** — Opik observability/prompt management + Ragas eval set
- [ ] **Phase 10** — CI, deployment polish, docs

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

1. **Ingestion** — upload PDF/DOCX → parse → chunk (clause/section-aware) → embed → vectors
   into Qdrant, metadata + full text into Postgres.
2. **Agentic query** — user asks a question → orchestrator runs a tool-calling loop against
   the active LLM provider, choosing from `retrieve_chunks`, `compare_regulations`,
   `generate_action_items`, `summarize_regulation` → every claim is grounded in retrieved
   chunks and cited back to its source clause/page.

**Multi-provider LLM layer** — one `LLMProvider` port, `AnthropicProvider` and `OpenAIProvider`
adapters behind it, selected via config with a fallback chain. The point isn't "support two
SDKs," it's a system that keeps working if one vendor is rate-limited or down.

**Auth/RBAC** — JWT-based, roles: CRO, Compliance Officer, Risk, Auditor, Ops.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Frontend | Streamlit |
| Vector store | Qdrant |
| Relational store | PostgreSQL |
| LLM | Anthropic Claude + OpenAI, behind a shared provider abstraction |
| Package/workspace management | uv |
| Tooling | ruff, black, mypy (strict), pytest, pre-commit |

## Getting started

```bash
# Install dependencies for every workspace package
make sync

# Start Postgres + Qdrant
make infra-up

# In separate terminals
make run-api   # http://localhost:8000
make run-ui    # http://localhost:8501
```

Copy `.env.example` to `.env` and fill in API keys before Phase 4 (LLM integration) lands.

## Development

```bash
make lint        # ruff
make format       # black + ruff --fix
make typecheck     # mypy --strict
make test           # pytest
```

## Roadmap

Built incrementally, one phase per commit/PR — see commit history for progress.

- [x] **Phase 0** — Repo scaffold: uv workspace, tooling, Docker Compose skeleton
- [x] **Phase 1** — Domain layer: entities, value objects, unit tests
- [ ] **Phase 2** — Infrastructure: Postgres models + Alembic, Qdrant client wrapper
- [ ] **Phase 3** — Document ingestion pipeline
- [ ] **Phase 4** — LLM provider abstraction (Anthropic + OpenAI, fallback router)
- [ ] **Phase 5** — Retrieval: hybrid search + citation grounding
- [ ] **Phase 6** — Agent orchestrator: tool-calling loop
- [ ] **Phase 7** — FastAPI endpoints + JWT auth/RBAC
- [ ] **Phase 8** — Streamlit UI: upload, chat, comparison, action-item dashboard
- [ ] **Phase 9** — Observability + groundedness eval set
- [ ] **Phase 10** — CI, deployment polish, docs

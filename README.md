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
│   ├── infrastructure/      Adapters implementing those ports: GroqProvider,
│   │                       QdrantVectorStore, PostgresDocumentRepository,
│   │                       PDF/DOCX parsers, regulation-aware chunker
│   └── shared/               Config, logging, exceptions — the shared kernel
├── deployment/              Docker Compose (Postgres, Qdrant, and later the apps)
└── tests/
```

**Two core flows:**

1. **Ingestion** — upload PDF/DOCX → parse → chunk (clause/section-aware) → embed
   (local `fastembed` model) → vectors into Qdrant, metadata + full text into Postgres.
2. **Agentic query** — user asks a question → a LangGraph agent runs a tool-calling loop against
   Groq (Llama models), choosing from `retrieve_chunks`, `compare_regulations`,
   `generate_action_items`, `summarize_regulation` → every claim is grounded in retrieved
   chunks and cited back to its source clause/page.

**Retrieval (`retrieve_chunks`)** — dense and sparse (BM25) search run together, both via local
`fastembed` models in the same Qdrant collection, and are fused with Qdrant's native RRF, then
the fused candidates are reranked with a local cross-encoder for a final precision pass.
Deliberately *not* included yet: HyDE (hypothetical-document query expansion) — dense+sparse+
RRF+rerank is already a strong baseline, and HyDE adds an LLM call (cost + latency) to every
query. It's a candidate to add later, driven by what the Phase 9 Ragas evals show is actually
missing, not added speculatively now.

**Zero-cost by design** — every external-API dependency in this stack was deliberately chosen
to have a free path: Groq's free tier for the LLM, local `fastembed` models for both dense and
sparse embeddings, a local cross-encoder for reranking. Anyone can clone this repo, grab a free
Groq API key, and run the whole thing without paying for or licensing anything. The
`LLMProvider`/`EmbeddingProvider` ports still make it a contained change to swap in
Anthropic/OpenAI/Cohere later if higher quality is worth the cost — the abstraction doesn't
disappear just because there's currently one adapter behind each port.

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
| LLM | Groq (Llama models) via the `groq` SDK, behind an `LLMProvider` port |
| Embeddings | Local `fastembed` — `BAAI/bge-small-en-v1.5` (dense) + BM25 (sparse), no API key |
| Reranker | Local cross-encoder, no API key |
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

Copy `.env.example` to `.env`. A free `GROQ_API_KEY` from [console.groq.com](https://console.groq.com)
is the only credential needed once Phase 4 (LLM integration) lands — embeddings and reranking
run entirely locally, no key required.

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
- [x] **Phase 3** — Document ingestion pipeline: parsing, regulation-aware chunking, local
      dense (`fastembed`) + BM25 sparse embeddings — switched from OpenAI embeddings after
      Phase 3 shipped, once the goal became sharing this app without any paid API key (see
      Phase 4 note)
- [x] **Phase 4** — LLM provider abstraction: `LLMProvider` port (with tool-calling built into
      its shape from the start, for Phase 6) + GroqProvider adapter, free-tier Llama models —
      chosen over the original Anthropic+OpenAI multi-provider plan specifically so the app can
      be cloned and run by anyone with zero paid API keys. Verified against the real API,
      including a full tool-call round trip
- [x] **Phase 5** — Retrieval: `RetrieveChunksUseCase` — hybrid dense+BM25 search fused with
      RRF (Phase 2), local cross-encoder rerank, citation grounding. Proven end-to-end with a
      real ingest-then-retrieve integration test against live Postgres + Qdrant, not just unit
      tests with fakes (HyDE deliberately deferred — see Architecture)
- [x] **Phase 6** — Agent orchestrator: a hand-built LangGraph tool-calling loop over our own
      `LLMProvider` port (not LangChain's model wrappers, not `langgraph`'s prebuilt ReAct
      agent — vendor specifics stay behind our port). All four tools are real: `retrieve_chunks`,
      `summarize_regulation`, `compare_regulations`, `generate_action_items` (which grounds each
      generated item to specific citation indices, not the whole retrieved set — exercising the
      domain layer's "an ActionItem needs >=1 citation" invariant for real). Verified end-to-end:
      ingest a document, ask the live agent a question, get back a grounded, cited answer. A real
      run also surfaced Groq/Llama's occasional malformed tool-call output
      (`tool_use_failed`) — fixed with a bounded retry plus `temperature=0`, not papered over
- [ ] **Phase 7** — FastAPI endpoints + JWT auth/RBAC + NeMo Guardrails (input *and* output
      rails together — deferred from Phase 3 since NeMo's rails engine needs an LLM to run
      its checks, which doesn't exist until Phase 4; one combined config beats two partial ones)
- [ ] **Phase 8** — Streamlit UI: upload, chat, comparison, action-item dashboard
- [ ] **Phase 9** — Opik observability/prompt management + Ragas eval set
- [ ] **Phase 10** — CI, deployment polish, docs

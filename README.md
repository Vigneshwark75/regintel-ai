# RegIntel AI

**Enterprise Regulatory Intelligence Platform — Agentic RAG**

**Live UI**: [regintel-ai.streamlit.app](https://regintel-ai.streamlit.app) — the frontend is
hosted (Streamlit Community Cloud, free); the backend (Postgres/Qdrant/FastAPI) isn't hosted
yet, so login will show a "can't reach the API" message until that lands. That's expected, not
broken — see the Roadmap.

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

**Guardrails** — NeMo Guardrails around both directions, via a `Guardrails` port so the engine
itself is swappable: every ingested chunk is screened for prompt-injection/jailbreak patterns
before it's embedded and stored, the user's question is screened before it reaches the agent,
and the agent's final answer is screened for system-prompt leakage before being returned.
Configured with **no LLM at all** (`models: []` in NeMo's config) — dialog/response generation
is disabled per-call via `GenerationOptions`, so this only ever runs the fast, free,
pattern-matching rail and never makes a network call of its own.

**Observability & evals** — every LLM call and agent step is traced in Opik, free tier,
completely inert (no network calls) when unconfigured. Retrieval and answer quality are
measured with Ragas (faithfulness, context precision/recall, answer relevancy) against a small
golden eval set.

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
| Auth | JWT (PyJWT), OAuth2 password flow, role-based access control |
| Guardrails | NeMo Guardrails, regex rails, no LLM required (input + output, behind a `Guardrails` port) |
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
is the only credential needed — embeddings and reranking run entirely locally, no key required.

### Trying the API

The API ships with a demo in-memory user per role (see `api/auth.py` — a real deployment
swaps this for an identity provider; nothing downstream changes since everything only cares
about the `(username, role)` pair a login produces):

| Username | Password | Role |
|---|---|---|
| `cro` | `cro-demo-password` | CRO |
| `compliance` | `compliance-demo-password` | Compliance Officer |
| `risk` | `risk-demo-password` | Risk |
| `auditor` | `auditor-demo-password` | Auditor |
| `ops` | `ops-demo-password` | Ops |

```bash
# Log in (OAuth2 password flow — also works via the "Authorize" button at /docs)
curl -X POST http://localhost:8000/auth/token \
  -d "username=compliance&password=compliance-demo-password"

# Upload a document (CRO/Compliance Officer only)
curl -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer <token>" \
  -F "file=@kyc_direction.docx" \
  -F "title=Master Direction on KYC" \
  -F "document_type=master_direction" \
  -F "reference_number=RBI/DBR/2016-17/18" \
  -F "issued_date=2016-02-25"

# Ask a grounded question (any authenticated role)
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"question": "How long must customer due diligence records be retained?"}'
```

Interactive docs (with the "Authorize" button pre-wired to `/auth/token`) are at
`http://localhost:8000/docs`.

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
- [x] **Phase 7a** — FastAPI endpoints + JWT auth/RBAC: `/auth/token`, `/documents` (upload,
      summarize, compare), `/ask`, `/action-items`, all wired to real Postgres/Qdrant/Groq
      through a composition root in `api/dependencies.py`. A real end-to-end test (login →
      upload → ask, over real HTTP) caught a genuine bug: the DB session dependency never
      committed, so every write silently rolled back on session close while Qdrant's write
      went through unconditionally — fixed by reusing the `session_scope()` helper Phase 2's
      own tests already relied on, instead of the subtly-different one written for the API
- [x] **Phase 7b** — NeMo Guardrails: `Guardrails` port + `NeMoGuardrailsService`, wired into
      both directions — `IngestDocumentUseCase` screens every chunk before it's embedded and
      stored, `ComplianceAgent.ask()` screens the incoming question and the outgoing answer.
      Configured with zero LLM (`models: []`); dialog/generation disabled per-call via
      `GenerationOptions`, so it's pure regex pattern-matching — free, no network call, and
      fast enough to be a regular unit test rather than an integration one. A "blocked" verdict
      is detected by comparing NeMo's output against the original text (pass-through vs.
      substituted) rather than string-matching its default refusal wording, which turned out
      not to be reliably reachable through custom Colang flows in this version — verified with
      a real prototype before committing to the approach, not assumed
- [x] **Phase 8** — Streamlit UI: login (JWT, role-aware), upload, ask (with citations),
      compare, action-item generation — all calling the real API via `api_client.py`, with
      `UI_API_BASE_URL` configurable for hosting the UI and API on different domains.
      Verified two ways: `AppTest`-based unit tests for structural rendering, `httpx`
      mock-transport tests for the API client's request construction, and a full manual
      click-through in a real browser against the live API/Postgres/Qdrant/Groq stack —
      login, page navigation, and a real grounded (and real ungrounded — "no citations
      returned" — path) `/ask` round trip all confirmed working end-to-end. Also deployed
      to Streamlit Community Cloud (free) — see the live link above. Two real deploy-time
      bugs found and fixed from actual build logs, not guessed: `uv sync` (no
      `--all-packages`) at the workspace root wasn't installing the UI's own dependencies at
      all (root `pyproject.toml` now lists `regintel-ui` as a dependency specifically so a
      plain `uv sync` — what hosting platforms invoke, with no way for us to pass flags —
      resolves everything needed), and a `streamlit`/`starlette` version pairing that only
      breaks on Python 3.14 (`.python-version` pins 3.12, what this project is actually
      tested against). Backend (Postgres/Qdrant/FastAPI) hosting deliberately deferred to
      Phase 10 rather than rushed here
- [x] **Phase 9a** — Opik tracing: `@opik.track` on `GroqProvider.complete()` (LLM calls),
      `ComplianceAgent._dispatch()` (each tool call), and `ask()` (the whole interaction as one
      trace). Fully disabled — zero network calls, not just "logged out" — when no
      `OPIK_API_KEY` is set, verified by reproducing the noisy default behavior first (failed
      auth requests on every span) and then confirming `opik.set_tracing_active(False)` at
      startup eliminates it entirely. Prompt versioning (Opik's `Prompt`/`ChatPrompt` objects)
      deliberately deferred — our system prompts are already versioned, just via git rather
      than a separate system, which is arguably the more standard answer at this project's
      size. Verified against real Opik Cloud through the actual production path (the running
      API, not a bypassed test double): a real `/ask` request produced
      `POST .../spans/batch` and `POST .../traces/batch`, both `204 No Content` — genuine
      successful trace uploads, confirmed in the server log, not assumed from a lack of errors
- [ ] **Phase 9b** — Ragas eval set
- [ ] **Phase 10** — CI, deployment polish, docs — including hosting the backend
      (Postgres/Qdrant/FastAPI) so the live UI is fully functional, not just reachable

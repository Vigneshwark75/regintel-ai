# Deploying the backend

Hosts Postgres + the FastAPI API on Render (free tier) and the vector store on
Qdrant Cloud (free tier) — the two services the README's roadmap had deferred. The
Streamlit UI is already deployed; this just points it at a real backend instead of
an unreachable `localhost`.

**Before you start, a real constraint:** Render's free web service has 512 MB RAM.
This app loads two local ML models in-process (the `fastembed` dense/sparse
embedders and the cross-encoder reranker) plus NeMo Guardrails and the LangGraph
agent. That combination is tight for 512 MB and may OOM on first request. If it
does, the fix is Render's paid Starter plan (~$7/mo, 512 MB → more), not a code
change — try free first, upgrade only if you actually hit the ceiling.

None of the steps below require me to create accounts or hold your credentials —
you do the signups and paste secrets into each platform's own dashboard.

## 1. Qdrant Cloud (vector store)

1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io) (free tier: 1 GB cluster).
2. Create a cluster. Once it's up, copy its **Cluster URL** and generate an **API
   key**.
3. Keep both handy for step 3.

## 2. Render (Postgres + API)

This repo has a `render.yaml` Blueprint that provisions both together.

1. Sign up at [render.com](https://render.com) and connect your GitHub account.
2. **New → Blueprint**, pick the `regintel-ai` repo. Render reads `render.yaml` and
   proposes a Postgres database (`regintel-postgres`) and a web service
   (`regintel-api`).
3. Before applying, it'll prompt for the env vars marked `sync: false`:
   - `QDRANT_URL`, `QDRANT_API_KEY` — from step 1.
   - `GROQ_API_KEY` — free key from [console.groq.com](https://console.groq.com).
   - `OPIK_API_KEY` — optional, leave blank to keep tracing disabled.
   - `UI_API_BASE_URL` — leave blank for now; Streamlit's URL isn't relevant to the
     API's own behavior, this field exists for symmetry with local `.env`.
   - `POSTGRES_DSN` — leave blank during the initial apply; Render needs to create
     `regintel-postgres` first before its connection string exists (see next step).
4. Apply the blueprint. Once `regintel-postgres` is provisioned, open its dashboard
   and copy the **Internal Database URL**. It looks like:
   `postgresql://regintel:<password>@<host>/regintel`
   Change the scheme to `postgresql+psycopg://` (this app uses the psycopg3 driver)
   and paste the result into `regintel-api`'s `POSTGRES_DSN` env var, then trigger a
   manual deploy.
5. Watch the deploy logs. The container runs `alembic upgrade head` before starting
   `uvicorn` (see `Dockerfile`), so a successful boot means migrations already
   applied — no separate migration step needed.
6. Confirm it's up: `https://regintel-api-<random>.onrender.com/docs` should load
   the FastAPI interactive docs.

**Free-tier cold starts:** Render's free web services sleep after ~15 minutes of
inactivity and take 30–60s to wake on the next request — expected, not a bug.

## 3. Point the Streamlit UI at it

The UI is already live at the link in the README. In Streamlit Community Cloud:

1. Open the app → **Settings → Secrets**.
2. Add `UI_API_BASE_URL = "https://regintel-api-<random>.onrender.com"` (your
   actual Render URL from step 2.6).
3. Save — Streamlit restarts the app automatically. Log in with one of the demo
   users (see the main README) and confirm `/ask` returns a real, cited answer.

## Rollback

Nothing here is destructive to existing state: the local dev stack
(`make infra-up`) is untouched, and this only adds a second, hosted set of the same
services. To undo, delete the Render services/database and the Qdrant Cloud
cluster from their respective dashboards, and remove `UI_API_BASE_URL` from
Streamlit's secrets to fall back to the "can't reach the API" state described in
the README.

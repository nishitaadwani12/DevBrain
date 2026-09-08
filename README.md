<div align="center">

# 🧠 DevBrain — AI Knowledge & Codebase Agent Platform

**Chat with your documents and entire GitHub repositories. Get streaming, citation-backed answers, an AI-drawn architecture graph, and a tool-calling agent — all in one workspace.**

FastAPI · React + TypeScript · Google Gemini · Supabase (Postgres + pgvector) · tree-sitter

</div>

---

## Overview

DevBrain is a full-stack, multi-user **Retrieval-Augmented Generation (RAG)** platform. Upload PDFs, Word docs, Markdown, or a `.zip` of code — **or paste any public GitHub repo URL** — and DevBrain ingests it, indexes it, and lets you ask questions in natural language. Every answer streams back token-by-token with **exact citations** (page numbers for documents, `file:line` for code), remembers the conversation, and can invoke a **tool-calling agent** that searches, compares, and explains across your whole knowledge base.

It is the productized evolution of a hackathon-winning knowledge assistant — a real system, not a single-file demo.

## Features

- **Multi-document workspaces** — group related documents and repositories, and query them together with per-user isolation.
- **RepoLens** — paste a GitHub repo → semantic (tree-sitter) code indexing across 15+ languages, an interactive **architecture dependency graph**, and an **AI-generated architecture overview**.
- **Cited answers** — every response links to the exact source; a **confidence score** flags weakly-grounded answers (a real RAG failure mode).
- **Streaming chat with memory** — Server-Sent Events stream the answer live; follow-up questions carry context; **suggested follow-ups** keep the conversation moving.
- **Tool-calling agent** — Gemini function-calling over `search_documents`, `compare_documents`, and `explain_architecture`, with a **live tool-step reasoning stream**.
- **Multi-user auth** — Supabase JWT; every query scoped per-user and per-workspace.
- **Async ingestion** — uploads and repo clones process in the background with live `processing → ready` status.

## Architecture

```
Upload / GitHub URL
       │
       ▼
Parse (PDF/DOCX/MD) │ Clone + tree-sitter code chunking      ← async background task
       │
       ▼
Chunk (page / file:line metadata) → Gemini embeddings → pgvector (Supabase)
       │
       ▼
Query → embed → workspace-scoped vector search → cited prompt → Gemini (streamed)
       │                                                   │
       ▼                                                   ▼
Conversation memory (Postgres)                      Tool-calling agent
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a module-by-module breakdown.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Flow, React Query, framer-motion |
| Backend | FastAPI (Python), async ingestion pipeline, Server-Sent Events |
| LLM + embeddings | Google Gemini (`gemini-flash`, `gemini-embedding-001`) |
| Vector store + DB | Supabase Postgres + pgvector |
| Code parsing | tree-sitter (15+ languages) |
| Auth + storage | Supabase |
| Testing | pytest (89 tests) |
| Deployment | Render (API) · Vercel (web) · Supabase — zero infrastructure cost |

## API Surface

```
POST   /workspaces                              GET  /workspaces
POST   /workspaces/{id}/documents/upload        GET  /workspaces/{id}/documents
POST   /workspaces/{id}/repos/ingest            GET  /repos/{id}/graph · /repos/{id}/overview
POST   /workspaces/{id}/search
POST   /workspaces/{id}/chat            (SSE, cited + streaming)
POST   /workspaces/{id}/agent · /agent/stream   (tool-calling, SSE)
POST   /workspaces/{id}/followups
GET    /workspaces/{id}/conversations · /conversations/{id}/messages
```

## Getting Started

**Prerequisites:** Python 3.12+, Node 18+, a Google Gemini API key, and a Supabase project.

```bash
# 1. Database — run docs/schema.sql in the Supabase SQL Editor.

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # add your Gemini key + Supabase URL/keys + DATABASE_URL
uvicorn app.main:app --reload

# 3. Frontend
cd frontend
npm install
cp .env.example .env         # set VITE_API_URL + Supabase URL/anon key
npm run dev
```

Backend runs at `http://localhost:8000` (interactive docs at `/docs`); the web app at `http://localhost:5173`.

Run the test suite:

```bash
cd backend && pytest        # 89 tests
```

## Deployment

Zero-cost, three services: **Render** (backend, via the included [`render.yaml`](render.yaml) blueprint), **Vercel** (frontend, root `frontend/`), and **Supabase** (Postgres + auth + pgvector). Full walkthrough in [`docs/SETUP.md`](docs/SETUP.md).

## Testing

89 automated tests cover parsing, token/semantic chunking, retrieval and prompt construction, agent tool-dispatch, SSE event sequencing, and every API route. External services (Gemini, the database, git clone) are mocked at their boundaries, and tree-sitter parsing plus import-graph resolution are exercised for real.

## License

MIT

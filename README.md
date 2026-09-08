# DevBrain — AI Knowledge Agent Platform

Upload documents **or paste a GitHub repo URL**, then chat with an AI agent that answers with
**exact citations**, remembers the conversation, calls tools to search/summarize/compare, and can
**explain a codebase's architecture** with a dependency graph.

DevBrain is the productized, open-source evolution of a hackathon-winning knowledge assistant — a full
RAG + tool-calling agent platform with multi-user auth, not a single-file Q&A demo.

## Features

- **Multi-document workspaces** — group related docs/repos (and `.zip` code archives) and query them together
- **RepoLens** — paste any public GitHub repo → semantic (tree-sitter) code indexing, an interactive
  **architecture/dependency graph**, and an **AI-generated architecture overview**
- **Cited answers** — every response links to the exact source (page for docs, `path:line` for code),
  with an **answer-confidence score** that flags weakly-grounded answers
- **Streaming chat** with conversation memory (follow-up questions carry context) + **suggested follow-ups**
- **Tool-calling agent** — `search_documents`, `list_documents`, `explain_architecture`,
  `compare_documents`; with a **streaming variant** that emits each tool step live
- **Evaluation harness** — pure retrieval/citation scoring + golden dataset (`backend/eval/`)
- **Multi-user auth** — Supabase JWT; every query scoped per-user/workspace

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React + TypeScript (Vite), Tailwind, React Flow, React Query |
| Backend | FastAPI (Python), async ingestion pipeline |
| LLM + embeddings | Google Gemini (`gemini-2.0-flash`, `text-embedding-004`) |
| Vector store + DB | Supabase Postgres + pgvector |
| Code parsing | tree-sitter (15+ languages) |
| Auth + storage | Supabase |

## Architecture

```
Upload / GitHub URL
      │
      ▼
Parse (PDF/DOCX/MD) │ Clone + tree-sitter code chunking   ← async background task
      │
      ▼
Chunk (page / path:line metadata) → Gemini embeddings → pgvector
      │
      ▼
Query → embed → vector search (workspace-scoped) → cited prompt → Gemini (stream)
      │                                                    │
      ▼                                                    ▼
Conversation memory (Postgres)                     Tool-calling agent
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

## API surface

`/workspaces` · `/workspaces/{id}/documents` · `/workspaces/{id}/repos/ingest` ·
`/repos/{id}/graph` · `/repos/{id}/overview` · `/workspaces/{id}/search` ·
`/workspaces/{id}/chat` (SSE) · `/workspaces/{id}/agent` · `/workspaces/{id}/agent/stream` (SSE) ·
`/workspaces/{id}/followups` · `/workspaces/{id}/conversations` · `/conversations/{id}/messages`

## Getting Started

See [`docs/SETUP.md`](docs/SETUP.md). TL;DR: run `docs/schema.sql` in Supabase, fill the `.env`
files, `uvicorn app.main:app --reload` (backend) and `npm run dev` (frontend).

Backend tests: `cd backend && ./.venv/bin/python -m pytest` (88 tests, fully mocked/offline).

## License

MIT

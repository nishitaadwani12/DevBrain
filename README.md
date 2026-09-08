# DevBrain — AI Knowledge Agent Platform

Upload your documents, then chat with an AI agent that answers with **exact citations**, remembers the
conversation, and can **search, summarize, and compare across your whole workspace**.

DevBrain is the productized, open-source evolution of a hackathon-winning knowledge assistant. It is a
full RAG + tool-calling agent platform with multi-user auth — not a single-file Q&A demo.

## Features

- **Multi-document workspaces** — group related docs and query them together
- **Cited answers** — every response links back to the exact source chunk (page / paragraph)
- **Conversation memory** — follow-up questions carry context
- **Tool-calling agent** — `search_docs`, `summarize`, `compare_docs`
- **Multi-user auth** — per-user documents with row-level security

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React + TypeScript (Vite), Tailwind, shadcn/ui |
| Backend | FastAPI (Python) |
| LLM + embeddings | Google Gemini (`gemini-2.0-flash`, `text-embedding-004`) |
| Vector store + DB | Supabase Postgres + pgvector |
| Auth + storage | Supabase |

## Repo Layout

```
backend/    FastAPI app (RAG pipeline + agent)
frontend/   React + TS client
docs/        Architecture notes
```

## Getting Started

See [`docs/SETUP.md`](docs/SETUP.md).

## License

MIT

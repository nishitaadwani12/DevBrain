# Architecture

## Overview

DevBrain is a RAG + tool-calling agent platform. A FastAPI backend handles ingestion, retrieval,
streaming chat, and an agent loop; a React frontend provides chat, document/repo management, and an
architecture-graph viewer. Supabase provides Postgres (+ pgvector), auth, and storage.

## Backend modules (`backend/app`)

| Module | Responsibility |
|---|---|
| `core/config.py` | Env-driven settings (Gemini, Supabase, auth toggle) |
| `core/auth.py` | Supabase JWT (HS256) verification → current user; dev bypass |
| `core/deps.py` | `require_workspace` ownership dependency |
| `services/parsing.py` | PDF/DOCX/MD/TXT → page-tagged segments |
| `services/chunking.py` | Token-aware chunking with page attribution |
| `services/code_chunking.py` | tree-sitter semantic chunking (funcs/classes) with `path:line` |
| `services/embeddings.py` | Gemini `text-embedding-004` (retrieval doc/query task types) |
| `services/vectorstore.py` | Workspaces/documents/chunks + pgvector cosine search (user-scoped) |
| `services/ingestion.py` | Doc pipeline: parse → chunk → embed → store (background) |
| `services/repo_ingest.py` | Clone repo → walk/filter files → code-chunk → embed → store |
| `services/repo_graph.py` | File dependency graph (Python + JS/TS import resolution) |
| `services/rag.py` | Retrieve + numbered-source, history-aware prompt building |
| `services/llm.py` | Gemini chat (streaming + non-streaming) |
| `services/agent.py` | Function-calling loop + pure tool dispatch |
| `services/conversation_store.py` | Conversation + message persistence |
| `api/*` | HTTP routers (workspaces, documents, repos, search, chat, conversations, agent) |

## Data model (`docs/schema.sql`)

- `workspaces (user_id, name)` — top-level container, owned by a Supabase user.
- `documents (workspace_id, user_id, source_type, source_url, status, graph, …)` — an upload or repo.
- `chunks (document_id, workspace_id, content, page | source_path/start_line/end_line, embedding vector(768))`.
- `conversations (workspace_id, user_id, title)` + `messages (conversation_id, role, content, citations)`.

All reads are scoped by `user_id`/`workspace_id` in SQL, because the backend connects with the Supabase
service key (bypassing RLS).

## Key flows

**Ingestion (async):** upload/URL creates a `documents` row with `status='processing'` and schedules a
background task. The task parses/clones, chunks, embeds in batches, inserts chunks, (for repos) builds
the dependency graph, and flips status to `ready` (or `failed` with an error).

**Retrieval + chat (SSE):** the query is embedded and matched against workspace chunks by cosine
distance. A prompt is built with numbered sources + recent conversation history, and Gemini's response
is streamed token-by-token over Server-Sent Events. Citations are emitted first so the UI can render the
source panel while the answer streams. Both user and assistant turns are persisted.

**Agent:** Gemini function-calling drives a bounded loop over `search_documents`, `list_documents`, and
`explain_architecture`. Tool dispatch is a pure function (unit-tested); the LLM loop is thin.

## Testing

67 backend tests run fully offline — Gemini, the database, and git clone are mocked at their seams, and
tree-sitter parsing + import-graph resolution are exercised for real. Auth and workspace-ownership
dependencies are overridden via a pytest fixture (`tests/conftest.py`).

-- DevBrain schema — run in the Supabase SQL Editor.
-- Covers all phases: workspaces + multi-user scoping, documents/chunks,
-- conversations/messages, and the RepoLens architecture graph.

create extension if not exists vector;
create extension if not exists "pgcrypto";  -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Workspaces (owned by a Supabase auth user)
-- ---------------------------------------------------------------------------
create table if not exists workspaces (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null,
    name       text not null,
    created_at timestamptz not null default now()
);
create index if not exists workspaces_user_idx on workspaces(user_id);

-- ---------------------------------------------------------------------------
-- Documents (uploaded files or ingested GitHub repos)
-- ---------------------------------------------------------------------------
create table if not exists documents (
    id           uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    user_id      uuid not null,
    filename     text not null,
    file_type    text not null,
    source_type  text not null default 'upload',  -- upload | github
    source_url   text,
    status       text not null default 'processing',  -- processing | ready | failed
    chunk_count  integer,
    error        text,
    graph        jsonb,   -- RepoLens architecture graph (github sources)
    overview     text,    -- AI-generated architecture overview (github sources)
    created_at   timestamptz not null default now()
);
create index if not exists documents_workspace_idx on documents(workspace_id);
create index if not exists documents_user_idx on documents(user_id);

-- ---------------------------------------------------------------------------
-- Chunks (embedded pieces of a document)
-- ---------------------------------------------------------------------------
create table if not exists chunks (
    id           uuid primary key default gen_random_uuid(),
    document_id  uuid not null references documents(id) on delete cascade,
    workspace_id uuid not null references workspaces(id) on delete cascade,
    content      text not null,
    chunk_index  integer not null,
    page         integer,       -- source page (uploaded docs)
    source_path  text,          -- file path within a repo (github sources)
    start_line   integer,
    end_line     integer,
    token_count  integer,
    embedding    vector(768) not null,  -- text-embedding-004 dimension
    created_at   timestamptz not null default now()
);
create index if not exists chunks_embedding_idx
    on chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index if not exists chunks_document_idx on chunks(document_id);
create index if not exists chunks_workspace_idx on chunks(workspace_id);

-- ---------------------------------------------------------------------------
-- Conversations + messages (chat memory)
-- ---------------------------------------------------------------------------
create table if not exists conversations (
    id           uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    user_id      uuid not null,
    title        text not null default 'New conversation',
    created_at   timestamptz not null default now()
);
create index if not exists conversations_workspace_idx on conversations(workspace_id);

create table if not exists messages (
    id              uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id) on delete cascade,
    role            text not null,   -- user | assistant
    content         text not null,
    citations       jsonb,           -- list of citation objects (assistant turns)
    created_at      timestamptz not null default now()
);
create index if not exists messages_conversation_idx on messages(conversation_id, created_at);

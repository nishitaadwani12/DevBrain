-- DevBrain schema — run in the Supabase SQL Editor.
-- Phase 1: documents + embedded chunks. (workspace_id / user_id added in Phase 3.)

create extension if not exists vector;
create extension if not exists "pgcrypto";  -- for gen_random_uuid()

create table if not exists documents (
    id          uuid primary key default gen_random_uuid(),
    filename    text not null,
    file_type   text not null,
    status      text not null default 'processing',  -- processing | ready | failed
    chunk_count integer,
    error       text,
    created_at  timestamptz not null default now()
);

create table if not exists chunks (
    id           uuid primary key default gen_random_uuid(),
    document_id  uuid not null references documents(id) on delete cascade,
    content      text not null,
    chunk_index  integer not null,
    page         integer,
    token_count  integer,
    embedding    vector(768) not null,  -- text-embedding-004 dimension
    created_at   timestamptz not null default now()
);

-- Approximate nearest-neighbour index for cosine distance.
create index if not exists chunks_embedding_idx
    on chunks using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

create index if not exists chunks_document_id_idx on chunks(document_id);

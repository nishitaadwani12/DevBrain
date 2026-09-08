"""Postgres + pgvector storage: workspaces, documents, and embedded chunks.

All reads are scoped by ``user_id`` (and ``workspace_id`` where relevant) since
the backend connects with the Supabase service key and therefore bypasses RLS —
scoping is enforced in SQL here instead.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector

from app.core.config import get_settings
from app.services.chunking import Chunk


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set")
    conn = psycopg.connect(settings.database_url)
    try:
        register_vector(conn)
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------
def _row_to_workspace(r) -> dict:
    return {"id": str(r[0]), "user_id": str(r[1]), "name": r[2],
            "created_at": r[3].isoformat() if r[3] else None}


def create_workspace(user_id: str, name: str) -> dict:
    with get_conn() as conn:
        r = conn.execute(
            "insert into workspaces (user_id, name) values (%s, %s) "
            "returning id, user_id, name, created_at",
            (user_id, name),
        ).fetchone()
        conn.commit()
        return _row_to_workspace(r)


def list_workspaces(user_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "select id, user_id, name, created_at from workspaces "
            "where user_id = %s order by created_at desc",
            (user_id,),
        ).fetchall()
        return [_row_to_workspace(r) for r in rows]


def get_workspace(workspace_id: str, user_id: str) -> dict | None:
    with get_conn() as conn:
        r = conn.execute(
            "select id, user_id, name, created_at from workspaces "
            "where id = %s and user_id = %s",
            (workspace_id, user_id),
        ).fetchone()
        return _row_to_workspace(r) if r else None


def delete_workspace(workspace_id: str, user_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "delete from workspaces where id = %s and user_id = %s",
            (workspace_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
_DOC_COLUMNS = (
    "id, workspace_id, user_id, filename, file_type, source_type, source_url, "
    "status, chunk_count, error, created_at"
)


def _row_to_document(r) -> dict:
    return {
        "id": str(r[0]),
        "workspace_id": str(r[1]),
        "user_id": str(r[2]),
        "filename": r[3],
        "file_type": r[4],
        "source_type": r[5],
        "source_url": r[6],
        "status": r[7],
        "chunk_count": r[8],
        "error": r[9],
        "created_at": r[10].isoformat() if r[10] else None,
    }


def create_document(
    workspace_id: str,
    user_id: str,
    filename: str,
    file_type: str,
    source_type: str = "upload",
    source_url: str | None = None,
) -> str:
    with get_conn() as conn:
        row = conn.execute(
            """
            insert into documents
                (workspace_id, user_id, filename, file_type, source_type, source_url, status)
            values (%s, %s, %s, %s, %s, %s, 'processing')
            returning id
            """,
            (workspace_id, user_id, filename, file_type, source_type, source_url),
        ).fetchone()
        conn.commit()
        return str(row[0])


def set_document_status(
    document_id: str, status: str, chunk_count: int | None = None, error: str | None = None
) -> None:
    with get_conn() as conn:
        conn.execute(
            "update documents set status = %s, "
            "chunk_count = coalesce(%s, chunk_count), error = %s where id = %s",
            (status, chunk_count, error, document_id),
        )
        conn.commit()


def set_document_graph(document_id: str, graph: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "update documents set graph = %s where id = %s",
            (json.dumps(graph), document_id),
        )
        conn.commit()


def set_document_overview(document_id: str, overview: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "update documents set overview = %s where id = %s", (overview, document_id)
        )
        conn.commit()


def get_document_overview(document_id: str, user_id: str) -> str | None:
    with get_conn() as conn:
        r = conn.execute(
            "select overview from documents where id = %s and user_id = %s",
            (document_id, user_id),
        ).fetchone()
        return r[0] if r else None


def get_document_graph(document_id: str, user_id: str) -> dict | None:
    with get_conn() as conn:
        r = conn.execute(
            "select graph from documents where id = %s and user_id = %s",
            (document_id, user_id),
        ).fetchone()
        if not r or r[0] is None:
            return None
        return r[0] if isinstance(r[0], dict) else json.loads(r[0])


def insert_chunks(
    document_id: str, workspace_id: str, chunks: list[Chunk], embeddings: list[list[float]]
) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                insert into chunks
                    (document_id, workspace_id, content, chunk_index, page,
                     source_path, start_line, end_line, token_count, embedding)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        document_id, workspace_id, c.text, c.chunk_index, c.page,
                        c.source_path, c.start_line, c.end_line, c.token_count, emb,
                    )
                    for c, emb in zip(chunks, embeddings)
                ],
            )
        conn.commit()


def list_documents(workspace_id: str, user_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            f"select {_DOC_COLUMNS} from documents "
            "where workspace_id = %s and user_id = %s order by created_at desc",
            (workspace_id, user_id),
        ).fetchall()
        return [_row_to_document(r) for r in rows]


def get_document(document_id: str, user_id: str) -> dict | None:
    with get_conn() as conn:
        r = conn.execute(
            f"select {_DOC_COLUMNS} from documents where id = %s and user_id = %s",
            (document_id, user_id),
        ).fetchone()
        return _row_to_document(r) if r else None


def delete_document(document_id: str, user_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "delete from documents where id = %s and user_id = %s",
            (document_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Vector search (scoped to a workspace)
# ---------------------------------------------------------------------------
def search_chunks(workspace_id: str, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            select c.id, c.document_id, d.filename, c.content, c.page, c.chunk_index,
                   c.source_path, c.start_line, c.end_line,
                   c.embedding <=> %s as distance
              from chunks c
              join documents d on d.id = c.document_id
             where c.workspace_id = %s
             order by c.embedding <=> %s
             limit %s
            """,
            (query_embedding, workspace_id, query_embedding, top_k),
        ).fetchall()
        return [
            {
                "chunk_id": str(r[0]),
                "document_id": str(r[1]),
                "filename": r[2],
                "content": r[3],
                "page": r[4],
                "chunk_index": r[5],
                "source_path": r[6],
                "start_line": r[7],
                "end_line": r[8],
                "distance": float(r[9]),
            }
            for r in rows
        ]

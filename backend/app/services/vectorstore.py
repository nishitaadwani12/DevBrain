"""Postgres + pgvector storage for documents and their embedded chunks."""
from __future__ import annotations

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


def create_document(filename: str, file_type: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            """
            insert into documents (filename, file_type, status)
            values (%s, %s, 'processing')
            returning id
            """,
            (filename, file_type),
        ).fetchone()
        conn.commit()
        return str(row[0])


def set_document_status(
    document_id: str, status: str, chunk_count: int | None = None, error: str | None = None
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            update documents
               set status = %s,
                   chunk_count = coalesce(%s, chunk_count),
                   error = %s
             where id = %s
            """,
            (status, chunk_count, error, document_id),
        )
        conn.commit()


def insert_chunks(document_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                insert into chunks (document_id, content, chunk_index, page, token_count, embedding)
                values (%s, %s, %s, %s, %s, %s)
                """,
                [
                    (document_id, c.text, c.chunk_index, c.page, c.token_count, emb)
                    for c, emb in zip(chunks, embeddings)
                ],
            )
        conn.commit()


def list_documents() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            select id, filename, file_type, status, chunk_count, error, created_at
              from documents
             order by created_at desc
            """
        ).fetchall()
        return [
            {
                "id": str(r[0]),
                "filename": r[1],
                "file_type": r[2],
                "status": r[3],
                "chunk_count": r[4],
                "error": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]


def get_document(document_id: str) -> dict | None:
    with get_conn() as conn:
        r = conn.execute(
            """
            select id, filename, file_type, status, chunk_count, error, created_at
              from documents
             where id = %s
            """,
            (document_id,),
        ).fetchone()
        if not r:
            return None
        return {
            "id": str(r[0]),
            "filename": r[1],
            "file_type": r[2],
            "status": r[3],
            "chunk_count": r[4],
            "error": r[5],
            "created_at": r[6].isoformat() if r[6] else None,
        }


def search_chunks(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Cosine-distance nearest-neighbour search across all chunks."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            select c.id, c.document_id, d.filename, c.content, c.page, c.chunk_index,
                   c.embedding <=> %s as distance
              from chunks c
              join documents d on d.id = c.document_id
             order by c.embedding <=> %s
             limit %s
            """,
            (query_embedding, query_embedding, top_k),
        ).fetchall()
        return [
            {
                "chunk_id": str(r[0]),
                "document_id": str(r[1]),
                "filename": r[2],
                "content": r[3],
                "page": r[4],
                "chunk_index": r[5],
                "distance": float(r[6]),
            }
            for r in rows
        ]

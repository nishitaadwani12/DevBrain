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


def create_document(
    filename: str,
    file_type: str,
    source_type: str = "upload",
    source_url: str | None = None,
) -> str:
    with get_conn() as conn:
        row = conn.execute(
            """
            insert into documents (filename, file_type, source_type, source_url, status)
            values (%s, %s, %s, %s, 'processing')
            returning id
            """,
            (filename, file_type, source_type, source_url),
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
                insert into chunks
                    (document_id, content, chunk_index, page, source_path,
                     start_line, end_line, token_count, embedding)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        document_id, c.text, c.chunk_index, c.page, c.source_path,
                        c.start_line, c.end_line, c.token_count, emb,
                    )
                    for c, emb in zip(chunks, embeddings)
                ],
            )
        conn.commit()


_DOC_COLUMNS = "id, filename, file_type, source_type, source_url, status, chunk_count, error, created_at"


def _row_to_document(r) -> dict:
    return {
        "id": str(r[0]),
        "filename": r[1],
        "file_type": r[2],
        "source_type": r[3],
        "source_url": r[4],
        "status": r[5],
        "chunk_count": r[6],
        "error": r[7],
        "created_at": r[8].isoformat() if r[8] else None,
    }


def list_documents() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            f"select {_DOC_COLUMNS} from documents order by created_at desc"
        ).fetchall()
        return [_row_to_document(r) for r in rows]


def get_document(document_id: str) -> dict | None:
    with get_conn() as conn:
        r = conn.execute(
            f"select {_DOC_COLUMNS} from documents where id = %s",
            (document_id,),
        ).fetchone()
        return _row_to_document(r) if r else None


def search_chunks(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Cosine-distance nearest-neighbour search across all chunks."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            select c.id, c.document_id, d.filename, c.content, c.page, c.chunk_index,
                   c.source_path, c.start_line, c.end_line,
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
                "source_path": r[6],
                "start_line": r[7],
                "end_line": r[8],
                "distance": float(r[9]),
            }
            for r in rows
        ]

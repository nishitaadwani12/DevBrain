"""Persistence for chat conversations and their messages."""
from __future__ import annotations

import json

from app.services.vectorstore import get_conn


def _row_to_conversation(r) -> dict:
    return {"id": str(r[0]), "workspace_id": str(r[1]), "title": r[2],
            "created_at": r[3].isoformat() if r[3] else None}


def create_conversation(workspace_id: str, user_id: str, title: str) -> dict:
    with get_conn() as conn:
        r = conn.execute(
            "insert into conversations (workspace_id, user_id, title) values (%s, %s, %s) "
            "returning id, workspace_id, title, created_at",
            (workspace_id, user_id, title[:200]),
        ).fetchone()
        conn.commit()
        return _row_to_conversation(r)


def list_conversations(workspace_id: str, user_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "select id, workspace_id, title, created_at from conversations "
            "where workspace_id = %s and user_id = %s order by created_at desc",
            (workspace_id, user_id),
        ).fetchall()
        return [_row_to_conversation(r) for r in rows]


def get_conversation(conversation_id: str, user_id: str) -> dict | None:
    with get_conn() as conn:
        r = conn.execute(
            "select id, workspace_id, title, created_at from conversations "
            "where id = %s and user_id = %s",
            (conversation_id, user_id),
        ).fetchone()
        return _row_to_conversation(r) if r else None


def add_message(conversation_id: str, role: str, content: str, citations: list[dict] | None = None) -> dict:
    with get_conn() as conn:
        r = conn.execute(
            "insert into messages (conversation_id, role, content, citations) "
            "values (%s, %s, %s, %s) returning id, role, content, citations, created_at",
            (conversation_id, role, content, json.dumps(citations) if citations else None),
        ).fetchone()
        conn.commit()
        return _row_to_message(r)


def _row_to_message(r) -> dict:
    citations = r[3]
    if citations and not isinstance(citations, (list, dict)):
        citations = json.loads(citations)
    return {"id": str(r[0]), "role": r[1], "content": r[2],
            "citations": citations, "created_at": r[4].isoformat() if r[4] else None}


def list_messages(conversation_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "select id, role, content, citations, created_at from messages "
            "where conversation_id = %s order by created_at asc",
            (conversation_id,),
        ).fetchall()
        return [_row_to_message(r) for r in rows]

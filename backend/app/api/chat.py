"""Streaming cited-answer endpoint with conversation memory (SSE).

Event sequence:
  event: conversation -> {"conversation_id": ...}  (first, so the UI can track it)
  event: sources      -> {"citations": [...]}
  event: token        -> {"text": "..."}  (many)
  event: done         -> {}
  event: error        -> {"message": "..."}
"""
from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.deps import require_workspace
from app.models.schemas import ChatRequest
from app.services import conversation_store, llm, rag

router = APIRouter(tags=["chat"])

# Keep the prompt bounded: only feed the most recent turns back to the model.
_HISTORY_LIMIT = 8


def _sse(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


def _resolve_conversation(workspace: dict, req: ChatRequest) -> dict:
    if req.conversation_id:
        convo = conversation_store.get_conversation(req.conversation_id, workspace["user_id"])
        if not convo or convo["workspace_id"] != workspace["id"]:
            raise HTTPException(404, "Conversation not found")
        return convo
    title = req.query.strip()[:80] or "New conversation"
    return conversation_store.create_conversation(workspace["id"], workspace["user_id"], title)


def _event_stream(workspace: dict, req: ChatRequest, convo: dict) -> Iterator[str]:
    try:
        yield _sse("conversation", {"conversation_id": convo["id"], "title": convo["title"]})

        history = conversation_store.list_messages(convo["id"])[-_HISTORY_LIMIT:]
        conversation_store.add_message(convo["id"], "user", req.query)

        hits = rag.retrieve(workspace["id"], req.query, top_k=req.top_k)
        citations = [
            {
                "index": i + 1, "chunk_id": h["chunk_id"], "document_id": h["document_id"],
                "filename": h["filename"], "page": h.get("page"),
                "source_path": h.get("source_path"), "start_line": h.get("start_line"),
                "end_line": h.get("end_line"), "content": h["content"],
            }
            for i, h in enumerate(hits)
        ]
        yield _sse("sources", {"citations": citations})

        prompt = rag.build_prompt(req.query, hits, history=history)
        answer_parts: list[str] = []
        for token in llm.stream_answer(prompt):
            answer_parts.append(token)
            yield _sse("token", {"text": token})

        conversation_store.add_message(convo["id"], "assistant", "".join(answer_parts), citations)
        yield _sse("done", {})
    except Exception as exc:  # noqa: BLE001
        yield _sse("error", {"message": str(exc)[:300]})


@router.post("/workspaces/{workspace_id}/chat")
async def chat(req: ChatRequest, workspace: dict = Depends(require_workspace)) -> StreamingResponse:
    convo = _resolve_conversation(workspace, req)
    return StreamingResponse(
        _event_stream(workspace, req, convo),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

"""Streaming cited-answer endpoint (Server-Sent Events).

Event sequence:
  event: sources  -> JSON list of retrieved citations (sent first so the UI can
                     render the citation panel while the answer streams)
  event: token    -> a piece of the answer text (many)
  event: done     -> end of stream
  event: error    -> something failed
"""
from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest
from app.services import llm, rag

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


def _event_stream(req: ChatRequest) -> Iterator[str]:
    try:
        hits = rag.retrieve(req.query, top_k=req.top_k)
        citations = [
            {
                "index": i + 1,
                "chunk_id": h["chunk_id"],
                "document_id": h["document_id"],
                "filename": h["filename"],
                "page": h.get("page"),
                "content": h["content"],
            }
            for i, h in enumerate(hits)
        ]
        yield _sse("sources", {"citations": citations})

        prompt = rag.build_prompt(req.query, hits)
        for token in llm.stream_answer(prompt):
            yield _sse("token", {"text": token})

        yield _sse("done", {})
    except Exception as exc:  # noqa: BLE001 — surface failures to the client stream
        yield _sse("error", {"message": str(exc)[:300]})


@router.post("")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

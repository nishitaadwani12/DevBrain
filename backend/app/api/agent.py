"""Tool-calling agent endpoints (workspace-scoped, with conversation memory)."""
from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.deps import require_workspace
from app.models.schemas import AgentRequest, AgentResponse
from app.services import agent, conversation_store

router = APIRouter(tags=["agent"])

_HISTORY_LIMIT = 8


def _resolve_conversation(workspace: dict, conversation_id: str | None, query: str) -> dict:
    if conversation_id:
        convo = conversation_store.get_conversation(conversation_id, workspace["user_id"])
        if not convo or convo["workspace_id"] != workspace["id"]:
            raise HTTPException(404, "Conversation not found")
        return convo
    title = query.strip()[:80] or "New conversation"
    return conversation_store.create_conversation(workspace["id"], workspace["user_id"], title)


@router.post("/workspaces/{workspace_id}/agent", response_model=AgentResponse)
async def run_agent(req: AgentRequest, workspace: dict = Depends(require_workspace)) -> AgentResponse:
    convo = _resolve_conversation(workspace, req.conversation_id, req.query)
    history = conversation_store.list_messages(convo["id"])[-_HISTORY_LIMIT:]
    conversation_store.add_message(convo["id"], "user", req.query)

    result = agent.run_agent(workspace["id"], workspace["user_id"], req.query, history=history)

    conversation_store.add_message(convo["id"], "assistant", result["answer"], result["citations"])
    return AgentResponse(
        conversation_id=convo["id"],
        answer=result["answer"],
        citations=result["citations"],
        tool_trace=result["tool_trace"],
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _agent_stream(workspace: dict, req: AgentRequest, convo: dict) -> Iterator[str]:
    try:
        yield _sse("conversation", {"conversation_id": convo["id"], "title": convo["title"]})
        history = conversation_store.list_messages(convo["id"])[-_HISTORY_LIMIT:]
        conversation_store.add_message(convo["id"], "user", req.query)

        final = {"answer": "", "citations": [], "tool_trace": []}
        for event in agent.agent_events(workspace["id"], workspace["user_id"], req.query, history):
            if event["type"] == "final":
                final = {k: event[k] for k in ("answer", "citations", "tool_trace")}
                yield _sse("sources", {"citations": final["citations"]})
                yield _sse("answer", {"text": final["answer"]})
            else:
                yield _sse(event["type"], event)  # tool_call / tool_result

        conversation_store.add_message(convo["id"], "assistant", final["answer"], final["citations"])
        yield _sse("done", {})
    except Exception as exc:  # noqa: BLE001
        yield _sse("error", {"message": str(exc)[:300]})


@router.post("/workspaces/{workspace_id}/agent/stream")
async def run_agent_stream(req: AgentRequest, workspace: dict = Depends(require_workspace)) -> StreamingResponse:
    convo = _resolve_conversation(workspace, req.conversation_id, req.query)
    return StreamingResponse(
        _agent_stream(workspace, req, convo),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

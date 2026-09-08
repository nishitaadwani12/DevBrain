"""Tool-calling agent endpoint (workspace-scoped, with conversation memory)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import require_workspace
from app.models.schemas import AgentRequest, AgentResponse
from app.services import agent, conversation_store

router = APIRouter(tags=["agent"])

_HISTORY_LIMIT = 8


@router.post("/workspaces/{workspace_id}/agent", response_model=AgentResponse)
async def run_agent(req: AgentRequest, workspace: dict = Depends(require_workspace)) -> AgentResponse:
    if req.conversation_id:
        convo = conversation_store.get_conversation(req.conversation_id, workspace["user_id"])
        if not convo or convo["workspace_id"] != workspace["id"]:
            raise HTTPException(404, "Conversation not found")
    else:
        title = req.query.strip()[:80] or "New conversation"
        convo = conversation_store.create_conversation(workspace["id"], workspace["user_id"], title)

    history = conversation_store.list_messages(convo["id"])[-_HISTORY_LIMIT:]
    conversation_store.add_message(convo["id"], "user", req.query)

    result = agent.run_agent(workspace["id"], workspace["user_id"], req.query, history=history)

    conversation_store.add_message(
        convo["id"], "assistant", result["answer"], result["citations"]
    )
    return AgentResponse(
        conversation_id=convo["id"],
        answer=result["answer"],
        citations=result["citations"],
        tool_trace=result["tool_trace"],
    )

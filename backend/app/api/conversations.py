"""Conversation history endpoints (workspace-scoped)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import User, get_current_user
from app.core.deps import require_workspace
from app.models.schemas import ConversationSummary, MessageOut
from app.services import conversation_store

router = APIRouter(tags=["conversations"])


@router.get("/workspaces/{workspace_id}/conversations", response_model=list[ConversationSummary])
async def list_conversations(workspace: dict = Depends(require_workspace)) -> list[ConversationSummary]:
    return [
        ConversationSummary(**c)
        for c in conversation_store.list_conversations(workspace["id"], workspace["user_id"])
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(conversation_id: str, user: User = Depends(get_current_user)) -> list[MessageOut]:
    convo = conversation_store.get_conversation(conversation_id, user.id)
    if not convo:
        raise HTTPException(404, "Conversation not found")
    return [MessageOut(**m) for m in conversation_store.list_messages(conversation_id)]

"""Suggested follow-up questions endpoint (workspace-scoped)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import require_workspace
from app.models.schemas import FollowupRequest, FollowupResponse
from app.services import suggestions

router = APIRouter(tags=["suggestions"])


@router.post("/workspaces/{workspace_id}/followups", response_model=FollowupResponse)
async def followups(req: FollowupRequest, workspace: dict = Depends(require_workspace)) -> FollowupResponse:
    return FollowupResponse(suggestions=suggestions.generate_followups(req.question, req.answer))

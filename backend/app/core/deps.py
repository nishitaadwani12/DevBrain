"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Depends, HTTPException

from app.core.auth import User, get_current_user
from app.services import vectorstore


def require_workspace(
    workspace_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """Resolve a workspace path param and assert the caller owns it."""
    workspace = vectorstore.get_workspace(workspace_id, user.id)
    if workspace is None:
        raise HTTPException(404, "Workspace not found")
    return workspace

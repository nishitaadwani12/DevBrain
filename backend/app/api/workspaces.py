"""Workspace CRUD (each workspace groups documents + conversations)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import User, get_current_user
from app.models.schemas import WorkspaceCreate, WorkspaceSummary
from app.services import vectorstore

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceSummary)
async def create_workspace(
    body: WorkspaceCreate, user: User = Depends(get_current_user)
) -> WorkspaceSummary:
    name = body.name.strip() or "Untitled workspace"
    return WorkspaceSummary(**vectorstore.create_workspace(user.id, name))


@router.get("", response_model=list[WorkspaceSummary])
async def list_workspaces(user: User = Depends(get_current_user)) -> list[WorkspaceSummary]:
    return [WorkspaceSummary(**w) for w in vectorstore.list_workspaces(user.id)]


@router.get("/{workspace_id}", response_model=WorkspaceSummary)
async def get_workspace(workspace_id: str, user: User = Depends(get_current_user)) -> WorkspaceSummary:
    ws = vectorstore.get_workspace(workspace_id, user.id)
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return WorkspaceSummary(**ws)


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str, user: User = Depends(get_current_user)) -> dict:
    if not vectorstore.delete_workspace(workspace_id, user.id):
        raise HTTPException(404, "Workspace not found")
    return {"deleted": True}

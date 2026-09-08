"""Vector search endpoint (workspace-scoped)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import require_workspace
from app.models.schemas import ChunkHit, SearchRequest, SearchResponse
from app.services import rag

router = APIRouter(tags=["search"])


@router.post("/workspaces/{workspace_id}/search", response_model=SearchResponse)
async def search(req: SearchRequest, workspace: dict = Depends(require_workspace)) -> SearchResponse:
    hits = rag.retrieve(workspace["id"], req.query, top_k=req.top_k)
    return SearchResponse(
        query=req.query,
        results=[ChunkHit(**h) for h in hits],
        confidence=rag.confidence(hits),
    )

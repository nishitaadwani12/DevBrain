"""RepoLens endpoints: ingest a public GitHub repo + serve its architecture graph."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.core.auth import User, get_current_user
from app.core.deps import require_workspace
from app.models.schemas import DocumentSummary, RepoIngestRequest, UploadResponse
from app.services import vectorstore
from app.services.repo_ingest import RepoIngestError, process_repo, repo_name, validate_repo_url

router = APIRouter(tags=["repos"])


@router.post("/workspaces/{workspace_id}/repos/ingest", response_model=UploadResponse)
async def ingest_repo(
    req: RepoIngestRequest,
    background_tasks: BackgroundTasks,
    workspace: dict = Depends(require_workspace),
) -> UploadResponse:
    try:
        url = validate_repo_url(req.url)
    except RepoIngestError as exc:
        raise HTTPException(400, str(exc))

    name = repo_name(url)
    document_id = vectorstore.create_document(
        workspace["id"], workspace["user_id"], name, "repo",
        source_type="github", source_url=url,
    )
    background_tasks.add_task(process_repo, document_id, workspace["id"], url)

    doc = vectorstore.get_document(document_id, workspace["user_id"])
    return UploadResponse(
        document=DocumentSummary(**doc),
        message=f"Cloning and indexing {name}; processing in background.",
    )


@router.get("/repos/{document_id}/graph")
async def get_repo_graph(document_id: str, user: User = Depends(get_current_user)) -> dict:
    graph = vectorstore.get_document_graph(document_id, user.id)
    if graph is None:
        raise HTTPException(404, "Graph not available (repo still processing or not a repo)")
    return graph

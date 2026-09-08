"""RepoLens endpoints: ingest a public GitHub repo as a knowledge source."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.schemas import DocumentSummary, RepoIngestRequest, UploadResponse
from app.services import vectorstore
from app.services.repo_ingest import RepoIngestError, process_repo, repo_name, validate_repo_url

router = APIRouter(prefix="/repos", tags=["repos"])


@router.post("/ingest", response_model=UploadResponse)
async def ingest_repo(req: RepoIngestRequest, background_tasks: BackgroundTasks) -> UploadResponse:
    try:
        url = validate_repo_url(req.url)
    except RepoIngestError as exc:
        raise HTTPException(400, str(exc))

    name = repo_name(url)
    document_id = vectorstore.create_document(
        filename=name, file_type="repo", source_type="github", source_url=url
    )
    background_tasks.add_task(process_repo, document_id, url)

    doc = vectorstore.get_document(document_id)
    return UploadResponse(
        document=DocumentSummary(**doc),
        message=f"Cloning and indexing {name}; processing in background.",
    )

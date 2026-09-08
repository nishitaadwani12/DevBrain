"""Document upload and management endpoints (workspace-scoped)."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.core.auth import User, get_current_user
from app.core.deps import require_workspace
from app.models.schemas import DocumentSummary, UploadResponse
from app.services import vectorstore
from app.services.ingestion import process_archive, process_document
from app.services.parsing import is_supported

router = APIRouter(tags=["documents"])

MAX_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/workspaces/{workspace_id}/documents/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace: dict = Depends(require_workspace),
) -> UploadResponse:
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    is_zip = ext == "zip"
    if not is_zip and not is_supported(filename):
        raise HTTPException(400, "Unsupported file type (allowed: pdf, docx, md, txt, zip)")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 20 MB)")

    document_id = vectorstore.create_document(
        workspace["id"], workspace["user_id"], filename, ext,
        source_type="archive" if is_zip else "upload",
    )
    task = process_archive if is_zip else process_document
    background_tasks.add_task(task, document_id, workspace["id"], filename, data)

    doc = vectorstore.get_document(document_id, workspace["user_id"])
    return UploadResponse(
        document=DocumentSummary(**doc),
        message="Upload received; processing in background.",
    )


@router.get("/workspaces/{workspace_id}/documents", response_model=list[DocumentSummary])
async def list_documents(workspace: dict = Depends(require_workspace)) -> list[DocumentSummary]:
    return [
        DocumentSummary(**d)
        for d in vectorstore.list_documents(workspace["id"], workspace["user_id"])
    ]


@router.get("/documents/{document_id}", response_model=DocumentSummary)
async def get_document(document_id: str, user: User = Depends(get_current_user)) -> DocumentSummary:
    doc = vectorstore.get_document(document_id, user.id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return DocumentSummary(**doc)


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, user: User = Depends(get_current_user)) -> dict:
    if not vectorstore.delete_document(document_id, user.id):
        raise HTTPException(404, "Document not found")
    return {"deleted": True}

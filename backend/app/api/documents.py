"""Document upload and management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.models.schemas import DocumentSummary, UploadResponse
from app.services import vectorstore
from app.services.ingestion import process_document
from app.services.parsing import is_supported

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    filename = file.filename or "upload"
    if not is_supported(filename):
        raise HTTPException(400, "Unsupported file type (allowed: pdf, docx, md, txt)")
    ext = filename.rsplit(".", 1)[-1].lower()

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 20 MB)")

    document_id = vectorstore.create_document(filename, ext)
    background_tasks.add_task(process_document, document_id, filename, data)

    doc = vectorstore.get_document(document_id)
    return UploadResponse(
        document=DocumentSummary(**doc),
        message="Upload received; processing in background.",
    )


@router.get("", response_model=list[DocumentSummary])
async def list_documents() -> list[DocumentSummary]:
    return [DocumentSummary(**d) for d in vectorstore.list_documents()]


@router.get("/{document_id}", response_model=DocumentSummary)
async def get_document(document_id: str) -> DocumentSummary:
    doc = vectorstore.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return DocumentSummary(**doc)

"""Pydantic response/request models for the API."""
from __future__ import annotations

from pydantic import BaseModel


class DocumentSummary(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    chunk_count: int | None = None
    error: str | None = None
    created_at: str | None = None


class UploadResponse(BaseModel):
    document: DocumentSummary
    message: str


class ChunkHit(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    content: str
    page: int | None = None
    chunk_index: int
    distance: float


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResponse(BaseModel):
    query: str
    results: list[ChunkHit]

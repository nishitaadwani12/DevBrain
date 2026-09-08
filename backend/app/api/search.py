"""Vector search endpoint (Phase 2 will layer cited LLM answers on top)."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ChunkHit, SearchRequest, SearchResponse
from app.services import vectorstore
from app.services.embeddings import embed_query

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    query_embedding = embed_query(req.query)
    hits = vectorstore.search_chunks(query_embedding, top_k=req.top_k)
    return SearchResponse(query=req.query, results=[ChunkHit(**h) for h in hits])

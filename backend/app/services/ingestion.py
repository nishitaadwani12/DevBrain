"""End-to-end ingestion: parse -> chunk -> embed -> store.

Run as a background task so uploads return immediately while processing
happens asynchronously (document status transitions processing -> ready).
"""
from __future__ import annotations

import logging

from app.services import vectorstore
from app.services.chunking import chunk_segments
from app.services.embeddings import embed_documents
from app.services.parsing import parse_document

logger = logging.getLogger(__name__)

# Gemini embed_content accepts batches; keep them modest to stay within limits.
_EMBED_BATCH = 50


def process_document(document_id: str, workspace_id: str, filename: str, data: bytes) -> None:
    try:
        segments = parse_document(filename, data)
        if not segments:
            vectorstore.set_document_status(document_id, "failed", error="No extractable text")
            return

        chunks = chunk_segments(segments)
        if not chunks:
            vectorstore.set_document_status(document_id, "failed", error="No chunks produced")
            return

        embeddings: list[list[float]] = []
        for start in range(0, len(chunks), _EMBED_BATCH):
            batch = chunks[start : start + _EMBED_BATCH]
            embeddings.extend(embed_documents([c.text for c in batch]))

        vectorstore.insert_chunks(document_id, workspace_id, chunks, embeddings)
        vectorstore.set_document_status(document_id, "ready", chunk_count=len(chunks))
        logger.info("Processed document %s (%d chunks)", document_id, len(chunks))
    except Exception as exc:  # noqa: BLE001 — surface any failure to the document row
        logger.exception("Failed to process document %s", document_id)
        vectorstore.set_document_status(document_id, "failed", error=str(exc)[:500])

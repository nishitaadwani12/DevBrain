"""End-to-end ingestion: parse -> chunk -> embed -> store.

Run as a background task so uploads return immediately while processing
happens asynchronously (document status transitions processing -> ready).
"""
from __future__ import annotations

import io
import logging
import os
import zipfile

from app.services import vectorstore
from app.services.chunking import chunk_segments
from app.services.code_chunking import EXT_TO_LANG, chunk_code
from app.services.embeddings import embed_documents
from app.services.parsing import parse_document

logger = logging.getLogger(__name__)

# Gemini embed_content accepts batches; keep them modest to stay within limits.
_EMBED_BATCH = 50

# Archive ingestion (reuses RepoLens filters).
from app.services.repo_ingest import DOC_EXTS, MAX_CHUNKS, MAX_FILE_BYTES, MAX_FILES, SKIP_DIRS


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


def _skip_zip_member(name: str) -> bool:
    if name.endswith("/"):
        return True
    parts = name.split("/")
    if any(p in SKIP_DIRS or p.startswith(".") for p in parts[:-1]):
        return True
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return ext not in EXT_TO_LANG and ext not in DOC_EXTS


def process_archive(document_id: str, workspace_id: str, filename: str, data: bytes) -> None:
    """Ingest a .zip of files: chunk each supported member with path attribution."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            members = [m for m in zf.infolist() if not _skip_zip_member(m.filename)]
            all_chunks = []
            next_index = 0
            for m in members[:MAX_FILES]:
                if m.file_size > MAX_FILE_BYTES:
                    continue
                try:
                    text = zf.read(m.filename).decode("utf-8", errors="ignore")
                except Exception:  # noqa: BLE001
                    continue
                if not text.strip():
                    continue
                ext = m.filename.rsplit(".", 1)[-1].lower()
                path = m.filename.replace(os.sep, "/")
                chunks = chunk_code(text, ext, path, start_index=next_index)
                all_chunks.extend(chunks)
                next_index += len(chunks)
                if len(all_chunks) >= MAX_CHUNKS:
                    break

        if not all_chunks:
            vectorstore.set_document_status(document_id, "failed", error="No supported files in archive")
            return

        embeddings: list[list[float]] = []
        for start in range(0, len(all_chunks), _EMBED_BATCH):
            batch = all_chunks[start : start + _EMBED_BATCH]
            embeddings.extend(embed_documents([c.text for c in batch]))

        vectorstore.insert_chunks(document_id, workspace_id, all_chunks, embeddings)
        vectorstore.set_document_status(document_id, "ready", chunk_count=len(all_chunks))
    except zipfile.BadZipFile:
        vectorstore.set_document_status(document_id, "failed", error="Invalid zip archive")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process archive %s", document_id)
        vectorstore.set_document_status(document_id, "failed", error=str(exc)[:500])

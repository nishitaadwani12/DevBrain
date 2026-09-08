"""RepoLens: clone a public GitHub repo and ingest it as code-aware chunks.

Reuses the Phase 1 embed/store pipeline; the only new work is fetching source
files and chunking them semantically (see ``code_chunking``).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

from app.services import vectorstore
from app.services.code_chunking import chunk_code
from app.services.embeddings import embed_documents

logger = logging.getLogger(__name__)

ALLOWED_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}

# Text/doc extensions we ingest alongside code.
DOC_EXTS = {"md", "markdown", "rst", "txt"}

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "out", "target", "vendor",
    "__pycache__", ".venv", "venv", ".next", ".nuxt", ".idea", ".vscode",
    "coverage", ".mypy_cache", ".pytest_cache", ".turbo", "bin", "obj",
}

MAX_FILE_BYTES = 300 * 1024   # skip files larger than 300 KB
MAX_FILES = 400               # bound cost per repo
MAX_CHUNKS = 4000
_EMBED_BATCH = 50


class RepoIngestError(Exception):
    pass


def validate_repo_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("https", "http"):
        raise RepoIngestError("Repo URL must be an https URL")
    host = parsed.netloc.lower()
    if host not in ALLOWED_HOSTS:
        raise RepoIngestError(f"Unsupported host '{host}' (allowed: {', '.join(sorted(ALLOWED_HOSTS))})")
    if not parsed.path.strip("/"):
        raise RepoIngestError("Repo URL is missing an owner/name path")
    return url.strip()


def repo_name(url: str) -> str:
    path = urlparse(url).path.strip("/")
    name = path.rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def _clone(url: str, dest: str) -> None:
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", url, dest],
            check=True, capture_output=True, text=True, timeout=120,
        )
    except subprocess.CalledProcessError as exc:
        raise RepoIngestError(f"git clone failed: {exc.stderr.strip()[:200]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepoIngestError("git clone timed out") from exc


def _iter_source_files(root: str):
    """Yield (relative_path, extension) for ingestable files."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for filename in filenames:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            from app.services.code_chunking import EXT_TO_LANG
            if ext not in EXT_TO_LANG and ext not in DOC_EXTS:
                continue
            full = os.path.join(dirpath, filename)
            try:
                if os.path.getsize(full) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield os.path.relpath(full, root), ext
            count += 1
            if count >= MAX_FILES:
                return


def process_repo(document_id: str, url: str) -> None:
    tmp = tempfile.mkdtemp(prefix="repolens_")
    try:
        _clone(url, tmp)

        all_chunks = []
        next_index = 0
        for rel_path, ext in _iter_source_files(tmp):
            full = os.path.join(tmp, rel_path)
            try:
                text = open(full, "r", encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if not text.strip():
                continue
            chunks = chunk_code(text, ext, rel_path, start_index=next_index)
            all_chunks.extend(chunks)
            next_index += len(chunks)
            if len(all_chunks) >= MAX_CHUNKS:
                break

        if not all_chunks:
            vectorstore.set_document_status(document_id, "failed", error="No source files found")
            return

        embeddings: list[list[float]] = []
        for start in range(0, len(all_chunks), _EMBED_BATCH):
            batch = all_chunks[start : start + _EMBED_BATCH]
            embeddings.extend(embed_documents([c.text for c in batch]))

        vectorstore.insert_chunks(document_id, all_chunks, embeddings)
        vectorstore.set_document_status(document_id, "ready", chunk_count=len(all_chunks))
        logger.info("Ingested repo %s (%d chunks)", url, len(all_chunks))
    except RepoIngestError as exc:
        vectorstore.set_document_status(document_id, "failed", error=str(exc)[:500])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to ingest repo %s", url)
        vectorstore.set_document_status(document_id, "failed", error=str(exc)[:500])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

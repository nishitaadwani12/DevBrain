"""Ingestion pipeline tests with Gemini + DB mocked out."""
import io
import zipfile

from app.services import ingestion


def _make_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("src/main.py", "def run():\n    return 1\n")
        zf.writestr("README.md", "# Docs\n")
        zf.writestr("node_modules/junk.js", "skip me")   # skipped dir
        zf.writestr("logo.png", "\x89PNG")                # unsupported ext
    return buf.getvalue()


def test_process_archive_ingests_supported_members(monkeypatch):
    captured = {}
    monkeypatch.setattr(ingestion, "embed_documents", lambda texts: [[0.0] * 768 for _ in texts])
    monkeypatch.setattr(
        ingestion.vectorstore, "insert_chunks",
        lambda doc_id, ws_id, chunks, embs: captured.update(chunks=chunks),
    )
    monkeypatch.setattr(
        ingestion.vectorstore, "set_document_status",
        lambda doc_id, status, chunk_count=None, error=None: captured.update(status=status),
    )

    ingestion.process_archive("doc-z", "ws-1", "proj.zip", _make_zip())

    assert captured["status"] == "ready"
    paths = {c.source_path for c in captured["chunks"]}
    assert any(p.endswith("main.py") for p in paths)
    assert any(p.endswith("README.md") for p in paths)
    assert not any("node_modules" in p for p in paths)
    assert not any(p.endswith(".png") for p in paths)


def test_process_archive_bad_zip_marks_failed(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        ingestion.vectorstore, "set_document_status",
        lambda doc_id, status, chunk_count=None, error=None: captured.update(status=status, error=error),
    )
    ingestion.process_archive("doc-z", "ws-1", "bad.zip", b"not a zip")
    assert captured["status"] == "failed"


def test_process_document_success(monkeypatch):
    calls = {}

    monkeypatch.setattr(
        ingestion, "embed_documents", lambda texts: [[0.0] * 768 for _ in texts]
    )
    monkeypatch.setattr(
        ingestion.vectorstore,
        "insert_chunks",
        lambda doc_id, ws_id, chunks, embeddings: calls.setdefault("inserted", len(chunks)),
    )
    monkeypatch.setattr(
        ingestion.vectorstore,
        "set_document_status",
        lambda doc_id, status, chunk_count=None, error=None: calls.setdefault(
            "status", (status, chunk_count, error)
        ),
    )

    ingestion.process_document("doc-1", "ws-1", "notes.txt", b"content " * 500)

    assert calls["inserted"] > 0
    status, chunk_count, error = calls["status"]
    assert status == "ready"
    assert chunk_count == calls["inserted"]
    assert error is None


def test_process_document_no_text_marks_failed(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        ingestion.vectorstore,
        "set_document_status",
        lambda doc_id, status, chunk_count=None, error=None: captured.update(
            status=status, error=error
        ),
    )
    ingestion.process_document("doc-2", "ws-1", "empty.txt", b"   ")
    assert captured["status"] == "failed"
    assert "No extractable text" in captured["error"]


def test_process_document_embedding_error_marks_failed(monkeypatch):
    captured = {}

    def boom(_texts):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(ingestion, "embed_documents", boom)
    monkeypatch.setattr(
        ingestion.vectorstore,
        "set_document_status",
        lambda doc_id, status, chunk_count=None, error=None: captured.update(
            status=status, error=error
        ),
    )
    ingestion.process_document("doc-3", "ws-1", "notes.txt", b"content " * 500)
    assert captured["status"] == "failed"
    assert "gemini down" in captured["error"]

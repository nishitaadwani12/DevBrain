"""Ingestion pipeline tests with Gemini + DB mocked out."""
from app.services import ingestion


def test_process_document_success(monkeypatch):
    calls = {}

    monkeypatch.setattr(
        ingestion, "embed_documents", lambda texts: [[0.0] * 768 for _ in texts]
    )
    monkeypatch.setattr(
        ingestion.vectorstore,
        "insert_chunks",
        lambda doc_id, chunks, embeddings: calls.setdefault("inserted", len(chunks)),
    )
    monkeypatch.setattr(
        ingestion.vectorstore,
        "set_document_status",
        lambda doc_id, status, chunk_count=None, error=None: calls.setdefault(
            "status", (status, chunk_count, error)
        ),
    )

    ingestion.process_document("doc-1", "notes.txt", b"content " * 500)

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
    ingestion.process_document("doc-2", "empty.txt", b"   ")
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
    ingestion.process_document("doc-3", "notes.txt", b"content " * 500)
    assert captured["status"] == "failed"
    assert "gemini down" in captured["error"]

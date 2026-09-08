"""Documents + search API tests (workspace-scoped, services mocked)."""
from app.api import documents as documents_api
from app.services import rag, vectorstore


def _doc(doc_id="doc-1", status="processing"):
    return {
        "id": doc_id, "workspace_id": "ws-1", "user_id": "user-123",
        "filename": "notes.txt", "file_type": "txt", "source_type": "upload",
        "source_url": None, "status": status, "chunk_count": None,
        "error": None, "created_at": None,
    }


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_accepts_supported_file(client, monkeypatch):
    scheduled = {}
    monkeypatch.setattr(vectorstore, "create_document", lambda *a, **k: "doc-1")
    monkeypatch.setattr(vectorstore, "get_document", lambda doc_id, user_id: _doc())
    monkeypatch.setattr(documents_api, "process_document", lambda *a, **k: scheduled.setdefault("ran", True))

    resp = client.post(
        "/workspaces/ws-1/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document"]["id"] == "doc-1"
    assert body["document"]["workspace_id"] == "ws-1"
    assert scheduled.get("ran") is True


def test_upload_rejects_unsupported_type(client):
    resp = client.post(
        "/workspaces/ws-1/documents/upload",
        files={"file": ("pic.png", b"\x89PNG", "image/png")},
    )
    assert resp.status_code == 400


def test_upload_rejects_empty_file(client):
    resp = client.post(
        "/workspaces/ws-1/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400


def test_get_document_404(client, monkeypatch):
    monkeypatch.setattr(vectorstore, "get_document", lambda doc_id, user_id: None)
    resp = client.get("/documents/missing")
    assert resp.status_code == 404


def test_search_returns_hits(client, monkeypatch):
    monkeypatch.setattr(
        rag, "retrieve",
        lambda ws, q, top_k=5: [
            {"chunk_id": "c1", "document_id": "d1", "filename": "notes.txt",
             "content": "relevant text", "page": 3, "chunk_index": 0,
             "source_path": None, "start_line": None, "end_line": None, "distance": 0.12}
        ],
    )
    resp = client.post("/workspaces/ws-1/search", json={"query": "what is devbrain", "top_k": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "what is devbrain"
    assert body["results"][0]["page"] == 3


def test_upload_requires_auth(anon_client):
    resp = anon_client.post(
        "/workspaces/ws-1/documents/upload",
        files={"file": ("notes.txt", b"hi", "text/plain")},
    )
    assert resp.status_code == 401

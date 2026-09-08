"""API tests using FastAPI TestClient with services mocked."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import documents as documents_api
from app.api import search as search_api
from app.services import vectorstore


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_accepts_supported_file(client, monkeypatch):
    scheduled = {}
    monkeypatch.setattr(vectorstore, "create_document", lambda fn, ext: "doc-1")
    monkeypatch.setattr(
        vectorstore,
        "get_document",
        lambda doc_id: {
            "id": doc_id, "filename": "notes.txt", "file_type": "txt",
            "status": "processing", "chunk_count": None, "error": None, "created_at": None,
        },
    )
    # prevent real background processing
    monkeypatch.setattr(
        documents_api, "process_document",
        lambda *a, **k: scheduled.setdefault("ran", True),
    )

    resp = client.post("/documents/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["document"]["id"] == "doc-1"
    assert body["document"]["status"] == "processing"
    assert scheduled.get("ran") is True  # background task fired


def test_upload_rejects_unsupported_type(client):
    resp = client.post("/documents/upload", files={"file": ("pic.png", b"\x89PNG", "image/png")})
    assert resp.status_code == 400


def test_upload_rejects_empty_file(client, monkeypatch):
    resp = client.post("/documents/upload", files={"file": ("empty.txt", b"", "text/plain")})
    assert resp.status_code == 400


def test_get_document_404(client, monkeypatch):
    monkeypatch.setattr(vectorstore, "get_document", lambda doc_id: None)
    resp = client.get("/documents/missing")
    assert resp.status_code == 404


def test_search_returns_hits(client, monkeypatch):
    monkeypatch.setattr(search_api, "embed_query", lambda q: [0.0] * 768)
    monkeypatch.setattr(
        vectorstore,
        "search_chunks",
        lambda emb, top_k=5: [
            {
                "chunk_id": "c1", "document_id": "d1", "filename": "notes.txt",
                "content": "relevant text", "page": 3, "chunk_index": 0, "distance": 0.12,
            }
        ],
    )
    resp = client.post("/search", json={"query": "what is devbrain", "top_k": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "what is devbrain"
    assert body["results"][0]["page"] == 3
    assert body["results"][0]["filename"] == "notes.txt"

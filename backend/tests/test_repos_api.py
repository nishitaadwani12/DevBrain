from app.api import repos as repos_api
from app.services import vectorstore


def _repo_doc():
    return {
        "id": "repo-1", "workspace_id": "ws-1", "user_id": "user-123",
        "filename": "requests", "file_type": "repo", "source_type": "github",
        "source_url": "https://github.com/psf/requests", "status": "processing",
        "chunk_count": None, "error": None, "created_at": None,
    }


def test_ingest_repo_schedules_processing(client, monkeypatch):
    scheduled = {}
    monkeypatch.setattr(vectorstore, "create_document", lambda *a, **k: "repo-1")
    monkeypatch.setattr(vectorstore, "get_document", lambda doc_id, user_id: _repo_doc())
    monkeypatch.setattr(repos_api, "process_repo", lambda *a, **k: scheduled.setdefault("ran", True))

    resp = client.post("/workspaces/ws-1/repos/ingest", json={"url": "https://github.com/psf/requests"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["document"]["source_type"] == "github"
    assert body["document"]["file_type"] == "repo"
    assert scheduled.get("ran") is True


def test_ingest_repo_rejects_bad_url(client):
    resp = client.post("/workspaces/ws-1/repos/ingest", json={"url": "git@github.com:psf/requests.git"})
    assert resp.status_code == 400


def test_get_repo_graph(client, monkeypatch):
    graph = {"nodes": [{"id": "a.py"}], "edges": [], "stats": {"file_count": 1}}
    monkeypatch.setattr(vectorstore, "get_document_graph", lambda doc_id, user_id: graph)
    resp = client.get("/repos/repo-1/graph")
    assert resp.status_code == 200
    assert resp.json()["stats"]["file_count"] == 1


def test_get_repo_graph_404_when_absent(client, monkeypatch):
    monkeypatch.setattr(vectorstore, "get_document_graph", lambda doc_id, user_id: None)
    resp = client.get("/repos/repo-1/graph")
    assert resp.status_code == 404


def test_get_repo_overview(client, monkeypatch):
    monkeypatch.setattr(vectorstore, "get_document_overview", lambda doc_id, user_id: "## Overview\nStuff")
    resp = client.get("/repos/repo-1/overview")
    assert resp.status_code == 200
    assert "Overview" in resp.json()["overview"]


def test_get_repo_overview_404_when_absent(client, monkeypatch):
    monkeypatch.setattr(vectorstore, "get_document_overview", lambda doc_id, user_id: None)
    resp = client.get("/repos/repo-1/overview")
    assert resp.status_code == 404

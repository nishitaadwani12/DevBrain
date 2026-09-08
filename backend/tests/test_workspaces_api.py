from app.services import vectorstore


def _ws(ws_id="ws-1", name="Test Workspace"):
    return {"id": ws_id, "user_id": "user-123", "name": name, "created_at": None}


def test_create_workspace(client, monkeypatch):
    monkeypatch.setattr(vectorstore, "create_workspace", lambda uid, name: _ws(name=name))
    resp = client.post("/workspaces", json={"name": "My Docs"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Docs"
    assert resp.json()["user_id"] == "user-123"


def test_list_workspaces(client, monkeypatch):
    monkeypatch.setattr(vectorstore, "list_workspaces", lambda uid: [_ws(), _ws("ws-2", "Other")])
    resp = client.get("/workspaces")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_workspace_404(client, monkeypatch):
    monkeypatch.setattr(vectorstore, "get_workspace", lambda wid, uid: None)
    resp = client.get("/workspaces/nope")
    assert resp.status_code == 404


def test_delete_workspace(client, monkeypatch):
    monkeypatch.setattr(vectorstore, "delete_workspace", lambda wid, uid: True)
    resp = client.delete("/workspaces/ws-1")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_workspaces_require_auth(anon_client):
    assert anon_client.get("/workspaces").status_code == 401

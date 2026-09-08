from app.services import conversation_store


def test_list_conversations(client, monkeypatch):
    monkeypatch.setattr(
        conversation_store, "list_conversations",
        lambda ws, uid: [{"id": "c1", "workspace_id": "ws-1", "title": "T", "created_at": None}],
    )
    resp = client.get("/workspaces/ws-1/conversations")
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "T"


def test_get_messages(client, monkeypatch):
    monkeypatch.setattr(
        conversation_store, "get_conversation",
        lambda cid, uid: {"id": cid, "workspace_id": "ws-1", "title": "T", "created_at": None},
    )
    monkeypatch.setattr(
        conversation_store, "list_messages",
        lambda cid: [
            {"id": "m1", "role": "user", "content": "hi", "citations": None, "created_at": None},
            {"id": "m2", "role": "assistant", "content": "hello", "citations": [], "created_at": None},
        ],
    )
    resp = client.get("/conversations/c1/messages")
    assert resp.status_code == 200
    body = resp.json()
    assert [m["role"] for m in body] == ["user", "assistant"]


def test_get_messages_404(client, monkeypatch):
    monkeypatch.setattr(conversation_store, "get_conversation", lambda cid, uid: None)
    resp = client.get("/conversations/missing/messages")
    assert resp.status_code == 404

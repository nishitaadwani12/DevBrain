"""SSE /chat endpoint tests with retrieval, LLM, and persistence mocked."""
from app.services import conversation_store, llm, rag


def _parse_sse(text: str) -> list[tuple[str, str]]:
    events, event = [], None
    for line in text.splitlines():
        if line.startswith("event: "):
            event = line[len("event: "):]
        elif line.startswith("data: ") and event is not None:
            events.append((event, line[len("data: "):]))
    return events


def _stub_persistence(monkeypatch):
    monkeypatch.setattr(
        conversation_store, "create_conversation",
        lambda ws, uid, title: {"id": "conv-1", "workspace_id": "ws-1", "title": title, "created_at": None},
    )
    monkeypatch.setattr(conversation_store, "list_messages", lambda cid: [])
    monkeypatch.setattr(conversation_store, "add_message", lambda *a, **k: None)


def test_chat_streams_conversation_sources_tokens_done(client, monkeypatch):
    _stub_persistence(monkeypatch)
    monkeypatch.setattr(
        rag, "retrieve",
        lambda ws, q, top_k=5: [
            {"chunk_id": "c1", "document_id": "d1", "filename": "notes.txt",
             "content": "DevBrain is a RAG platform", "page": 2, "chunk_index": 0,
             "source_path": None, "start_line": None, "end_line": None, "distance": 0.1}
        ],
    )
    monkeypatch.setattr(llm, "stream_answer", lambda prompt: iter(["Dev", "Brain", " [1]"]))

    resp = client.post("/workspaces/ws-1/chat", json={"query": "what is devbrain?"})
    assert resp.status_code == 200
    kinds = [e for e, _ in _parse_sse(resp.text)]

    assert kinds[0] == "conversation"
    assert "sources" in kinds
    assert kinds.count("token") == 3
    assert kinds[-1] == "done"


def test_chat_emits_error_event_on_failure(client, monkeypatch):
    _stub_persistence(monkeypatch)

    def boom(ws, q, top_k=5):
        raise RuntimeError("db offline")

    monkeypatch.setattr(rag, "retrieve", boom)
    resp = client.post("/workspaces/ws-1/chat", json={"query": "x"})
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert any(kind == "error" and "db offline" in data for kind, data in events)

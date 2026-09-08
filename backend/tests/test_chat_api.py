"""SSE /chat endpoint tests with retrieval + LLM mocked."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import chat as chat_api


@pytest.fixture
def client():
    return TestClient(app)


def _parse_sse(text: str) -> list[tuple[str, str]]:
    events = []
    event = None
    for line in text.splitlines():
        if line.startswith("event: "):
            event = line[len("event: "):]
        elif line.startswith("data: ") and event is not None:
            events.append((event, line[len("data: "):]))
    return events


def test_chat_streams_sources_tokens_done(client, monkeypatch):
    monkeypatch.setattr(
        chat_api.rag, "retrieve",
        lambda q, top_k=5: [
            {"chunk_id": "c1", "document_id": "d1", "filename": "notes.txt",
             "content": "DevBrain is a RAG platform", "page": 2, "chunk_index": 0, "distance": 0.1}
        ],
    )
    monkeypatch.setattr(chat_api.rag, "build_prompt", lambda q, hits: "PROMPT")
    monkeypatch.setattr(chat_api.llm, "stream_answer", lambda prompt: iter(["Dev", "Brain", " [1]"]))

    resp = client.post("/chat", json={"query": "what is devbrain?", "top_k": 5})
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    kinds = [e for e, _ in events]

    assert kinds[0] == "sources"
    assert "notes.txt" in events[0][1]
    assert kinds.count("token") == 3
    assert kinds[-1] == "done"


def test_chat_emits_error_event_on_failure(client, monkeypatch):
    def boom(q, top_k=5):
        raise RuntimeError("db offline")

    monkeypatch.setattr(chat_api.rag, "retrieve", boom)
    resp = client.post("/chat", json={"query": "x"})
    assert resp.status_code == 200  # stream opens, error delivered as an event
    events = _parse_sse(resp.text)
    assert any(kind == "error" and "db offline" in data for kind, data in events)

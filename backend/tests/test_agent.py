"""Agent tool-dispatch tests (pure) + agent API test (LLM mocked)."""
from app.api import agent as agent_api
from app.services import agent, conversation_store


def _hit(i):
    return {"chunk_id": f"c{i}", "document_id": "d1", "filename": "notes.txt",
            "content": f"content {i}", "page": None, "chunk_index": i,
            "source_path": "app/x.py", "start_line": 1, "end_line": 5, "distance": 0.1}


def test_dispatch_search_documents_accumulates_citations(monkeypatch):
    monkeypatch.setattr(agent.rag, "retrieve", lambda ws, q, top_k=5: [_hit(1), _hit(2)])
    citations = []
    result = agent.dispatch_tool("search_documents", {"query": "x"}, "ws-1", "u-1", citations)
    assert len(result["results"]) == 2
    assert len(citations) == 2
    assert citations[0]["index"] == 1
    assert result["results"][0]["location"] == "app/x.py"


def test_dispatch_list_documents(monkeypatch):
    monkeypatch.setattr(
        agent.vectorstore, "list_documents",
        lambda ws, uid: [{"id": "d1", "filename": "a.pdf", "file_type": "pdf",
                          "source_type": "upload", "status": "ready"}],
    )
    result = agent.dispatch_tool("list_documents", {}, "ws-1", "u-1", [])
    assert result["documents"][0]["filename"] == "a.pdf"


def test_dispatch_explain_architecture(monkeypatch):
    graph = {"stats": {"file_count": 3}, "edges": [
        {"source": "a.py", "target": "core.py"}, {"source": "b.py", "target": "core.py"}]}
    monkeypatch.setattr(agent.vectorstore, "get_document_graph", lambda did, uid: graph)
    result = agent.dispatch_tool("explain_architecture", {"document_id": "d1"}, "ws-1", "u-1", [])
    assert result["stats"]["file_count"] == 3
    assert result["top_files"][0]["file"] == "core.py"
    assert result["top_files"][0]["dependents"] == 2


def test_dispatch_compare_documents_groups_by_source(monkeypatch):
    hits = [
        {**_hit(1), "filename": "a.pdf"},
        {**_hit(2), "filename": "b.pdf"},
        {**_hit(3), "filename": "a.pdf"},
    ]
    monkeypatch.setattr(agent.rag, "retrieve", lambda ws, q, top_k=8: hits)
    citations = []
    result = agent.dispatch_tool("compare_documents", {"topic": "auth"}, "ws-1", "u-1", citations)
    groups = {g["document"]: g for g in result["by_document"]}
    assert set(groups) == {"a.pdf", "b.pdf"}
    assert len(groups["a.pdf"]["excerpts"]) == 2
    assert len(citations) == 3


def test_dispatch_unknown_tool():
    assert "Unknown tool" in agent.dispatch_tool("bogus", {}, "ws-1", "u-1", [])["error"]


def test_run_agent_returns_final(monkeypatch):
    def fake_events(ws, uid, q, history=None):
        yield {"type": "tool_call", "name": "search_documents", "args": {}}
        yield {"type": "final", "answer": "done [1]",
               "citations": [{"index": 1}], "tool_trace": ["search_documents"]}

    monkeypatch.setattr(agent, "agent_events", fake_events)
    result = agent.run_agent("ws-1", "u-1", "q")
    assert result["answer"] == "done [1]"
    assert result["tool_trace"] == ["search_documents"]


def test_agent_stream_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        conversation_store, "create_conversation",
        lambda ws, uid, title: {"id": "conv-1", "workspace_id": "ws-1", "title": title, "created_at": None},
    )
    monkeypatch.setattr(conversation_store, "list_messages", lambda cid: [])
    monkeypatch.setattr(conversation_store, "add_message", lambda *a, **k: None)

    def fake_events(ws, uid, q, history=None):
        yield {"type": "tool_call", "name": "search_documents", "args": {"query": "x"}}
        yield {"type": "tool_result", "name": "search_documents", "summary": "2 snippet(s)"}
        yield {"type": "final", "answer": "The answer [1]",
               "citations": [{"index": 1, "filename": "a.pdf"}], "tool_trace": ["search_documents"]}

    monkeypatch.setattr(agent_api.agent, "agent_events", fake_events)

    resp = client.post("/workspaces/ws-1/agent/stream", json={"query": "compare docs"})
    assert resp.status_code == 200
    kinds = []
    for line in resp.text.splitlines():
        if line.startswith("event: "):
            kinds.append(line[len("event: "):])
    assert kinds[0] == "conversation"
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "answer" in kinds
    assert kinds[-1] == "done"


def test_agent_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        conversation_store, "create_conversation",
        lambda ws, uid, title: {"id": "conv-1", "workspace_id": "ws-1", "title": title, "created_at": None},
    )
    monkeypatch.setattr(conversation_store, "list_messages", lambda cid: [])
    monkeypatch.setattr(conversation_store, "add_message", lambda *a, **k: None)
    monkeypatch.setattr(
        agent_api.agent, "run_agent",
        lambda ws, uid, query, history=None: {
            "answer": "The answer [1]",
            "citations": [{"index": 1, "filename": "notes.txt"}],
            "tool_trace": ["search_documents"],
        },
    )

    resp = client.post("/workspaces/ws-1/agent", json={"query": "how does auth work?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_id"] == "conv-1"
    assert body["answer"] == "The answer [1]"
    assert body["tool_trace"] == ["search_documents"]

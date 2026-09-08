from app.services import rag


def _hit(i, page=None):
    return {
        "chunk_id": f"c{i}", "document_id": "d1", "filename": "notes.txt",
        "content": f"content {i}", "page": page, "chunk_index": i, "distance": 0.1,
    }


def test_build_context_numbers_sources_and_includes_page():
    ctx = rag.build_context([_hit(1, page=4), _hit(2)])
    assert "[1] (notes.txt, p.4)" in ctx
    assert "[2] (notes.txt)" in ctx
    assert "content 1" in ctx and "content 2" in ctx


def test_build_prompt_includes_query_and_sources():
    prompt = rag.build_prompt("what is X?", [_hit(1)])
    assert "what is X?" in prompt
    assert "content 1" in prompt
    assert "citations" in prompt.lower()


def test_build_prompt_handles_no_hits():
    prompt = rag.build_prompt("anything", [])
    assert "don't have any relevant" in prompt
    assert "anything" in prompt


def test_retrieve_uses_embedding_and_store(monkeypatch):
    monkeypatch.setattr(rag, "embed_query", lambda q: [0.1] * 768)
    monkeypatch.setattr(
        rag.vectorstore, "search_chunks", lambda emb, top_k=5: [_hit(1)][:top_k]
    )
    hits = rag.retrieve("q", top_k=1)
    assert len(hits) == 1
    assert hits[0]["chunk_id"] == "c1"

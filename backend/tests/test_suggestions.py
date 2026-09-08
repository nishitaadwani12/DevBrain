from app.services import suggestions


def test_parse_followups_strips_numbering_and_dedupes():
    text = "1. What is X?\n- How does Y work?\nHow does Y work?\n\n3) Where is Z?"
    out = suggestions.parse_followups(text)
    assert out == ["What is X?", "How does Y work?", "Where is Z?"]


def test_parse_followups_limits_to_three():
    text = "a?\nb?\nc?\nd?\ne?"
    assert len(suggestions.parse_followups(text)) == 3


def test_generate_followups_uses_llm(monkeypatch):
    monkeypatch.setattr(suggestions.llm, "generate_answer", lambda p: "Q1?\nQ2?\nQ3?")
    out = suggestions.generate_followups("q", "a")
    assert out == ["Q1?", "Q2?", "Q3?"]


def test_followups_endpoint(client, monkeypatch):
    monkeypatch.setattr(suggestions, "generate_followups", lambda q, a: ["A?", "B?"])
    resp = client.post("/workspaces/ws-1/followups", json={"question": "q", "answer": "a"})
    assert resp.status_code == 200
    assert resp.json()["suggestions"] == ["A?", "B?"]

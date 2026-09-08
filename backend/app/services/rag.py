"""RAG orchestration: retrieve relevant chunks and build a cited prompt.

The prompt-building and citation logic here is deliberately pure (no network)
so it can be unit-tested without calling Gemini or the database.
"""
from __future__ import annotations

from app.services import vectorstore
from app.services.embeddings import embed_query

SYSTEM_INSTRUCTION = (
    "You are DevBrain, a knowledge assistant. Answer the user's question using ONLY "
    "the numbered sources provided. Cite the sources you use inline with bracketed "
    "numbers like [1] or [2]. If the sources do not contain the answer, say you don't "
    "know based on the provided documents. Be concise and accurate."
)


def confidence(hits: list[dict]) -> dict:
    """Estimate answer groundedness from retrieval distances.

    Cosine distance is in [0, 2] (0 = identical). We convert the best few hits to
    similarities and surface a 0-1 score plus a coarse label so the UI can warn
    when an answer is weakly grounded (a common RAG failure mode).
    """
    if not hits:
        return {"score": 0.0, "label": "none", "grounded": False}
    sims = sorted((1.0 - h.get("distance", 1.0) for h in hits), reverse=True)
    top = sims[0]
    avg_top = sum(sims[:3]) / len(sims[:3])
    score = max(0.0, min(1.0, round(0.6 * top + 0.4 * avg_top, 2)))
    label = "high" if score >= 0.72 else "medium" if score >= 0.5 else "low"
    return {"score": score, "label": label, "grounded": score >= 0.5}


def retrieve(workspace_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Embed the query and fetch the nearest chunks within a workspace."""
    query_embedding = embed_query(query)
    return vectorstore.search_chunks(workspace_id, query_embedding, top_k=top_k)


def build_context(hits: list[dict]) -> str:
    """Render retrieved chunks as a numbered source list for the prompt."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        if hit.get("source_path"):
            location = hit["source_path"]
            if hit.get("start_line") is not None:
                location += f":{hit['start_line']}"
                if hit.get("end_line") and hit["end_line"] != hit["start_line"]:
                    location += f"-{hit['end_line']}"
        else:
            location = hit["filename"]
            if hit.get("page") is not None:
                location += f", p.{hit['page']}"
        blocks.append(f"[{i}] ({location})\n{hit['content']}")
    return "\n\n".join(blocks)


def build_history(history: list[dict] | None) -> str:
    """Render prior turns so follow-up questions have context."""
    if not history:
        return ""
    lines = [f"{m['role'].capitalize()}: {m['content']}" for m in history]
    return "Conversation so far:\n" + "\n".join(lines) + "\n\n"


def build_prompt(query: str, hits: list[dict], history: list[dict] | None = None) -> str:
    history_block = build_history(history)
    if not hits:
        return (
            f"{SYSTEM_INSTRUCTION}\n\n{history_block}"
            "No sources were retrieved. Tell the user you don't have any relevant "
            f"documents to answer this.\n\nQuestion: {query}"
        )
    return (
        f"{SYSTEM_INSTRUCTION}\n\n{history_block}"
        f"Sources:\n{build_context(hits)}\n\n"
        f"Question: {query}\n\nAnswer (with inline [n] citations):"
    )

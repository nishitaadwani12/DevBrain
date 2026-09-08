"""Generate context-aware follow-up questions after an answer."""
from __future__ import annotations

from app.services import llm

_INSTRUCTION = (
    "Given a question and the answer that was given, propose 3 concise, specific follow-up "
    "questions the user might naturally ask next. Return ONLY the questions, one per line, with "
    "no numbering, bullets, or extra text."
)


def build_followups_prompt(question: str, answer: str) -> str:
    return f"{_INSTRUCTION}\n\nQuestion: {question}\n\nAnswer: {answer}\n\nFollow-up questions:"


def parse_followups(text: str, limit: int = 3) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip().lstrip("-*0123456789.) ").strip()
        if cleaned and cleaned.endswith("?"):
            out.append(cleaned)
        elif cleaned:
            out.append(cleaned)
    # de-dupe, preserve order
    seen, unique = set(), []
    for q in out:
        if q.lower() not in seen:
            seen.add(q.lower())
            unique.append(q)
    return unique[:limit]


def generate_followups(question: str, answer: str) -> list[str]:
    text = llm.generate_answer(build_followups_prompt(question, answer))
    return parse_followups(text)

"""Pure scoring functions for the RAG evaluation harness.

Kept dependency-free so they're unit-tested in isolation; the runner
(`eval/run_eval.py`) wires them to live retrieval/answers.
"""
from __future__ import annotations


def retrieval_recall(retrieved: list[str], expected: list[str]) -> float:
    """Fraction of expected source substrings found in any retrieved locator."""
    if not expected:
        return 1.0
    hits = sum(1 for e in expected if any(e.lower() in r.lower() for r in retrieved))
    return round(hits / len(expected), 3)


def citation_precision(cited: list[str], expected: list[str]) -> float:
    """Fraction of returned citations that match an expected source."""
    if not cited:
        return 0.0
    good = sum(1 for c in cited if any(e.lower() in c.lower() for e in expected))
    return round(good / len(cited), 3)


def answer_keyword_coverage(answer: str, keywords: list[str]) -> float:
    """Fraction of required keywords present in the answer."""
    if not keywords:
        return 1.0
    a = answer.lower()
    return round(sum(1 for k in keywords if k.lower() in a) / len(keywords), 3)


def aggregate(per_case: list[dict]) -> dict:
    """Average each numeric metric across cases."""
    if not per_case:
        return {}
    keys = {k for case in per_case for k, v in case.items() if isinstance(v, (int, float))}
    return {k: round(sum(c.get(k, 0.0) for c in per_case) / len(per_case), 3) for k in keys}

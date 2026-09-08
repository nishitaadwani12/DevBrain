"""Run the DevBrain retrieval evaluation against a live workspace.

Usage (from backend/, with .env configured and documents ingested):
    python -m eval.run_eval <workspace_id>

Reports per-case retrieval recall and the aggregate score. Requires GEMINI_API_KEY
and DATABASE_URL (it calls the real embedding + vector search path).
"""
from __future__ import annotations

import json
import os
import sys

from app.services import evaluation, rag

DATASET = os.path.join(os.path.dirname(__file__), "dataset.json")


def main(workspace_id: str) -> int:
    with open(DATASET) as f:
        cases = json.load(f)["cases"]

    per_case = []
    for case in cases:
        hits = rag.retrieve(workspace_id, case["question"], top_k=5)
        retrieved = [h.get("source_path") or h["filename"] for h in hits]
        recall = evaluation.retrieval_recall(retrieved, case.get("expected_sources", []))
        conf = rag.confidence(hits)["score"]
        per_case.append({"question": case["question"], "retrieval_recall": recall, "confidence": conf})
        print(f"[recall={recall:.2f} conf={conf:.2f}] {case['question']}")
        print(f"    retrieved: {retrieved}")

    agg = evaluation.aggregate(per_case)
    print("\nAGGREGATE:", json.dumps(agg))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))

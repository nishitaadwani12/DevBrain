from app.services import evaluation


def test_retrieval_recall():
    assert evaluation.retrieval_recall(["app/chunking.py", "app/rag.py"], ["chunking"]) == 1.0
    assert evaluation.retrieval_recall(["app/rag.py"], ["chunking", "rag"]) == 0.5
    assert evaluation.retrieval_recall(["x"], []) == 1.0  # nothing expected


def test_citation_precision():
    assert evaluation.citation_precision(["auth.py", "misc.py"], ["auth"]) == 0.5
    assert evaluation.citation_precision([], ["auth"]) == 0.0


def test_answer_keyword_coverage():
    assert evaluation.answer_keyword_coverage("It uses a JWT token", ["jwt", "token"]) == 1.0
    assert evaluation.answer_keyword_coverage("It uses a JWT", ["jwt", "token"]) == 0.5


def test_aggregate():
    agg = evaluation.aggregate([
        {"retrieval_recall": 1.0, "confidence": 0.8},
        {"retrieval_recall": 0.5, "confidence": 0.6},
    ])
    assert agg["retrieval_recall"] == 0.75
    assert agg["confidence"] == 0.7

from app.services import repo_overview
from app.services.repo_graph import SourceFile


def _graph():
    return {
        "nodes": [], "edges": [
            {"source": "a.py", "target": "core.py"},
            {"source": "b.py", "target": "core.py"},
        ],
        "stats": {"file_count": 3, "edge_count": 2, "languages": {"python": 3}},
    }


def test_build_overview_prompt_includes_repo_and_files():
    samples = [("core.py", "def core(): ..."), ("README.md", "# Project")]
    prompt = repo_overview.build_overview_prompt("myrepo", _graph(), samples)
    assert "myrepo" in prompt
    assert "core.py" in prompt
    assert "python (3)" in prompt
    assert "def core" in prompt


def test_select_samples_prioritizes_readme_and_top_files():
    files = [
        SourceFile(path="README.md", ext="md", text="readme"),
        SourceFile(path="core.py", ext="py", text="core"),
        SourceFile(path="a.py", ext="py", text="a"),
    ]
    samples = repo_overview.select_samples(files, _graph())
    paths = [p for p, _ in samples]
    assert "README.md" in paths
    assert "core.py" in paths  # most-depended-on file


def test_generate_overview_calls_llm(monkeypatch):
    monkeypatch.setattr(repo_overview.llm, "generate_answer", lambda prompt: "## Overview\nStuff")
    files = [SourceFile(path="core.py", ext="py", text="core")]
    out = repo_overview.generate_overview("myrepo", _graph(), files)
    assert "Overview" in out

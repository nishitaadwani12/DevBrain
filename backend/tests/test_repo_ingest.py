import os

import pytest

from app.services import repo_ingest
from app.services.repo_ingest import RepoIngestError, repo_name, validate_repo_url


def test_validate_accepts_github_https():
    assert validate_repo_url("https://github.com/psf/requests") == "https://github.com/psf/requests"


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:psf/requests.git",   # ssh
        "file:///etc/passwd",                # local file
        "https://evil.example.com/repo",     # disallowed host
        "https://github.com/",               # missing owner/name
    ],
)
def test_validate_rejects_bad_urls(url):
    with pytest.raises(RepoIngestError):
        validate_repo_url(url)


def test_repo_name_strips_git_suffix():
    assert repo_name("https://github.com/psf/requests.git") == "requests"
    assert repo_name("https://github.com/psf/requests") == "requests"


def test_process_repo_success(monkeypatch, tmp_path):
    # Fake `git clone` by writing a couple of source files into the dest dir.
    def fake_clone(url, dest):
        os.makedirs(os.path.join(dest, "src"), exist_ok=True)
        with open(os.path.join(dest, "src", "main.py"), "w") as f:
            f.write("def run():\n    return 1\n")
        with open(os.path.join(dest, "README.md"), "w") as f:
            f.write("# Project\n\nDocs here.\n")
        # a file that must be skipped
        os.makedirs(os.path.join(dest, "node_modules"), exist_ok=True)
        with open(os.path.join(dest, "node_modules", "junk.js"), "w") as f:
            f.write("skip me")

    captured = {}
    monkeypatch.setattr(repo_ingest, "_clone", fake_clone)
    monkeypatch.setattr(repo_ingest, "embed_documents", lambda texts: [[0.0] * 768 for _ in texts])
    monkeypatch.setattr(
        repo_ingest.vectorstore, "insert_chunks",
        lambda doc_id, chunks, embs: captured.update(chunks=chunks),
    )
    monkeypatch.setattr(
        repo_ingest.vectorstore, "set_document_status",
        lambda doc_id, status, chunk_count=None, error=None: captured.update(
            status=status, count=chunk_count
        ),
    )

    repo_ingest.process_repo("doc-1", "https://github.com/x/y")

    assert captured["status"] == "ready"
    assert captured["count"] > 0
    paths = {c.source_path for c in captured["chunks"]}
    assert any(p.endswith("main.py") for p in paths)
    assert any(p.endswith("README.md") for p in paths)
    # skipped directory not ingested
    assert not any("node_modules" in p for p in paths)


def test_process_repo_clone_failure_marks_failed(monkeypatch):
    def boom(url, dest):
        raise RepoIngestError("git clone failed: not found")

    captured = {}
    monkeypatch.setattr(repo_ingest, "_clone", boom)
    monkeypatch.setattr(
        repo_ingest.vectorstore, "set_document_status",
        lambda doc_id, status, chunk_count=None, error=None: captured.update(
            status=status, error=error
        ),
    )
    repo_ingest.process_repo("doc-2", "https://github.com/x/y")
    assert captured["status"] == "failed"
    assert "clone failed" in captured["error"]

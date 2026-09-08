"""Generate a README-style architecture overview for an ingested repo.

Prompt construction is pure (unit-tested); the LLM call is a thin wrapper.
"""
from __future__ import annotations

from app.services import llm

_MAX_SAMPLE_CHARS = 1200
_MAX_SAMPLES = 12

OVERVIEW_INSTRUCTION = (
    "You are a senior engineer writing a concise architecture overview of a codebase for a new "
    "contributor. Using the file list, dependency stats, and sampled file contents, describe: "
    "(1) what the project does, (2) the main entry points, (3) the key modules and how they relate, "
    "(4) notable data flow. Use short Markdown sections. Do not invent files that aren't shown."
)


def build_overview_prompt(repo_name: str, graph: dict, samples: list[tuple[str, str]]) -> str:
    stats = graph.get("stats", {})
    languages = ", ".join(f"{k} ({v})" for k, v in stats.get("languages", {}).items())
    top_files = _top_files(graph)

    sample_blocks = []
    for path, text in samples[:_MAX_SAMPLES]:
        sample_blocks.append(f"### {path}\n{text[:_MAX_SAMPLE_CHARS]}")

    return (
        f"{OVERVIEW_INSTRUCTION}\n\n"
        f"Repository: {repo_name}\n"
        f"Files: {stats.get('file_count', '?')} | Dependency edges: {stats.get('edge_count', '?')}\n"
        f"Languages: {languages or 'n/a'}\n"
        f"Most-depended-on files: {', '.join(top_files) or 'n/a'}\n\n"
        f"Sampled file contents:\n" + "\n\n".join(sample_blocks) +
        "\n\nWrite the architecture overview now:"
    )


def _top_files(graph: dict, n: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for e in graph.get("edges", []):
        counts[e["target"]] = counts.get(e["target"], 0) + 1
    return [f for f, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]]


def select_samples(source_files, graph: dict) -> list[tuple[str, str]]:
    """Pick representative files: READMEs + most-depended-on files."""
    by_path = {f.path: f for f in source_files}
    chosen: list[str] = []

    for path in by_path:
        base = path.rsplit("/", 1)[-1].lower()
        if base.startswith("readme"):
            chosen.append(path)

    for path in _top_files(graph, n=10):
        if path in by_path and path not in chosen:
            chosen.append(path)

    # Backfill with any remaining files if we're short.
    for path in by_path:
        if len(chosen) >= _MAX_SAMPLES:
            break
        if path not in chosen:
            chosen.append(path)

    return [(p, by_path[p].text) for p in chosen[:_MAX_SAMPLES]]


def generate_overview(repo_name: str, graph: dict, source_files) -> str:
    samples = select_samples(source_files, graph)
    prompt = build_overview_prompt(repo_name, graph, samples)
    return llm.generate_answer(prompt)

"""Build a file-level dependency graph for an ingested repo (RepoLens).

Extracts import statements per file and resolves them to other files in the same
repo, producing a nodes/edges graph the frontend renders with react-flow.
Resolution is best-effort for Python and JS/TS (relative imports); other
languages contribute nodes without edges.
"""
from __future__ import annotations

import os
import posixpath
import re
from collections import Counter
from dataclasses import dataclass

from app.services.code_chunking import language_for_extension

# Raw import-target extraction per language family.
_PY_FROM = re.compile(r"^\s*from\s+([.\w]+)\s+import\s+(.+)$", re.MULTILINE)
_PY_IMPORT = re.compile(r"^\s*import\s+([.\w]+(?:\s*,\s*[.\w]+)*)", re.MULTILINE)
_JS_IMPORT = re.compile(
    r"""(?:import[^'"]*from\s*['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|import\s*['"]([^'"]+)['"])"""
)

_JS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")


@dataclass
class SourceFile:
    path: str      # repo-relative, forward-slash
    ext: str
    text: str


def _norm(path: str) -> str:
    return path.replace(os.sep, "/")


def _python_targets(text: str) -> list[str]:
    targets: list[str] = []
    # `from a.b import c, d` -> a.b, a.b.c, a.b.d (c/d may be submodules)
    for m in _PY_FROM.finditer(text):
        base = m.group(1)
        targets.append(base)
        names = m.group(2).split("#", 1)[0]
        for name in names.replace("(", "").replace(")", "").split(","):
            token = name.strip().split(" as ")[0].strip()
            if token and token != "*":
                targets.append(f"{base}.{token}")
    # `import a.b.c, d`
    for m in _PY_IMPORT.finditer(text):
        for part in m.group(1).split(","):
            token = part.strip().split(" as ")[0].strip()
            if token:
                targets.append(token)
    return targets


def _js_targets(text: str) -> list[str]:
    targets = []
    for m in _JS_IMPORT.finditer(text):
        targets.append(m.group(1) or m.group(2) or m.group(3))
    return [t for t in targets if t]


def _resolve_python(module: str, path_set: set[str]) -> str | None:
    rel = module.lstrip(".").replace(".", "/")
    if not rel:
        return None
    for cand in (f"{rel}.py", f"{rel}/__init__.py"):
        for p in path_set:
            if p == cand or p.endswith("/" + cand):
                return p
    return None


def _resolve_js(spec: str, from_path: str, path_set: set[str]) -> str | None:
    if not spec.startswith("."):
        return None  # external package
    base = posixpath.normpath(posixpath.join(posixpath.dirname(from_path), spec))
    candidates = [base] + [base + e for e in _JS_EXTS] + [f"{base}/index{e}" for e in _JS_EXTS]
    for cand in candidates:
        if cand in path_set:
            return cand
    return None


def build_graph(files: list[SourceFile], max_nodes: int = 300) -> dict:
    files = files[:max_nodes]
    path_set = {f.path for f in files}
    languages = Counter()
    nodes = []
    for f in files:
        lang = language_for_extension(f.ext) or f.ext or "other"
        languages[lang] += 1
        nodes.append({"id": f.path, "label": posixpath.basename(f.path),
                      "dir": posixpath.dirname(f.path), "language": lang})

    edges = set()
    for f in files:
        lang = language_for_extension(f.ext)
        if lang == "python":
            for module in _python_targets(f.text):
                target = _resolve_python(module, path_set)
                if target and target != f.path:
                    edges.add((f.path, target))
        elif lang in ("javascript", "typescript", "tsx"):
            for spec in _js_targets(f.text):
                target = _resolve_js(spec, f.path, path_set)
                if target and target != f.path:
                    edges.add((f.path, target))

    return {
        "nodes": nodes,
        "edges": [{"source": s, "target": t} for s, t in sorted(edges)],
        "stats": {
            "file_count": len(nodes),
            "edge_count": len(edges),
            "languages": dict(languages),
        },
    }

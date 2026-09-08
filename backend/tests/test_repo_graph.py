from app.services.repo_graph import SourceFile, build_graph


def test_python_import_edges_resolved():
    files = [
        SourceFile(path="pkg/main.py", ext="py", text="from pkg import util\nimport pkg.helpers\n"),
        SourceFile(path="pkg/util.py", ext="py", text="x = 1\n"),
        SourceFile(path="pkg/helpers.py", ext="py", text="y = 2\n"),
    ]
    graph = build_graph(files)
    edges = {(e["source"], e["target"]) for e in graph["edges"]}
    assert ("pkg/main.py", "pkg/util.py") in edges
    assert ("pkg/main.py", "pkg/helpers.py") in edges
    assert graph["stats"]["file_count"] == 3
    assert graph["stats"]["languages"]["python"] == 3


def test_js_relative_import_resolved():
    files = [
        SourceFile(path="src/app.js", ext="js", text="import { f } from './lib/util';\n"),
        SourceFile(path="src/lib/util.js", ext="js", text="export const f = 1;\n"),
    ]
    graph = build_graph(files)
    edges = {(e["source"], e["target"]) for e in graph["edges"]}
    assert ("src/app.js", "src/lib/util.js") in edges


def test_external_imports_are_not_edges():
    files = [SourceFile(path="a.py", ext="py", text="import os\nimport requests\n")]
    graph = build_graph(files)
    assert graph["edges"] == []
    assert graph["stats"]["file_count"] == 1

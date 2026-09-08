from app.services.code_chunking import chunk_code, language_for_extension


PY_SOURCE = '''\
import os


def top_level(x):
    return x + 1


class Widget:
    def method(self):
        return 42
'''


def test_language_lookup():
    assert language_for_extension("py") == "python"
    assert language_for_extension("PY") == "python"
    assert language_for_extension("unknownext") is None


def test_python_chunks_by_definition_with_line_numbers():
    chunks = chunk_code(PY_SOURCE, "py", "pkg/mod.py")
    texts = [c.text for c in chunks]

    # function and class captured as separate semantic units
    assert any("def top_level" in t for t in texts)
    assert any("class Widget" in t for t in texts)
    # every chunk carries the file path
    assert all(c.source_path == "pkg/mod.py" for c in chunks)
    # line numbers are populated and 1-indexed
    fn_chunk = next(c for c in chunks if "def top_level" in c.text)
    assert fn_chunk.start_line == 4
    assert fn_chunk.end_line == 5


def test_leading_imports_captured_as_preamble():
    chunks = chunk_code(PY_SOURCE, "py", "pkg/mod.py")
    assert any("import os" in c.text for c in chunks)


def test_unsupported_extension_falls_back_to_token_chunks():
    text = "line one\nline two\nline three\n"
    chunks = chunk_code(text, "md", "README.md")
    assert len(chunks) >= 1
    assert chunks[0].source_path == "README.md"
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 3


def test_javascript_functions_detected():
    js = "function add(a, b) {\n  return a + b;\n}\n\nclass Foo {}\n"
    chunks = chunk_code(js, "js", "app.js")
    texts = " ".join(c.text for c in chunks)
    assert "function add" in texts
    assert "class Foo" in texts

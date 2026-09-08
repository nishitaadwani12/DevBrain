"""Code-aware chunking via tree-sitter.

Splits source files along semantic boundaries (functions, classes) instead of
blind token windows, and records the exact file path + line range so answers can
cite `path:line`. Falls back to token chunking for unsupported languages or
oversized definitions.
"""
from __future__ import annotations

from tree_sitter_language_pack import get_parser

from app.services.chunking import Chunk, count_tokens

# Extensions we treat as source code, mapped to tree-sitter language names.
EXT_TO_LANG: dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "tsx",
    "java": "java",
    "go": "go",
    "rs": "rust",
    "rb": "ruby",
    "c": "c",
    "h": "c",
    "cpp": "cpp",
    "cc": "cpp",
    "hpp": "cpp",
    "cs": "c_sharp",
    "php": "php",
    "kt": "kotlin",
    "swift": "swift",
    "scala": "scala",
}

# Top-level node types that represent a citable semantic unit, per language.
_DEFINITION_TYPES: dict[str, set[str]] = {
    "python": {"function_definition", "class_definition", "decorated_definition"},
    "javascript": {"function_declaration", "class_declaration", "method_definition", "lexical_declaration"},
    "typescript": {"function_declaration", "class_declaration", "method_definition", "interface_declaration", "lexical_declaration"},
    "tsx": {"function_declaration", "class_declaration", "method_definition", "interface_declaration", "lexical_declaration"},
    "java": {"class_declaration", "method_declaration", "interface_declaration", "enum_declaration"},
    "go": {"function_declaration", "method_declaration", "type_declaration"},
    "rust": {"function_item", "struct_item", "impl_item", "enum_item", "trait_item"},
    "ruby": {"method", "class", "module"},
    "c": {"function_definition", "struct_specifier"},
    "cpp": {"function_definition", "class_specifier", "struct_specifier"},
    "c_sharp": {"class_declaration", "method_declaration", "interface_declaration"},
}

_MAX_UNIT_TOKENS = 800  # split a definition larger than this


def language_for_extension(ext: str) -> str | None:
    return EXT_TO_LANG.get(ext.lower())


def _token_subchunks(text: str, chunk_tokens: int, overlap: int) -> list[str]:
    from app.services.chunking import _encoder

    tokens = _encoder.encode(text)
    if len(tokens) <= chunk_tokens:
        return [text]
    pieces, step = [], max(1, chunk_tokens - overlap)
    for start in range(0, len(tokens), step):
        window = tokens[start : start + chunk_tokens]
        if not window:
            break
        pieces.append(_encoder.decode(window))
        if start + chunk_tokens >= len(tokens):
            break
    return pieces


def _fallback_chunks(text: str, source_path: str, start_index: int) -> list[Chunk]:
    """Token-chunk an unsupported file, tagging the whole file's line span."""
    total_lines = max(1, len(text.splitlines()))
    chunks = []
    for i, piece in enumerate(_token_subchunks(text, 500, 60)):
        piece = piece.strip()
        if not piece:
            continue
        chunks.append(
            Chunk(
                text=piece,
                chunk_index=start_index + i,
                token_count=count_tokens(piece),
                source_path=source_path,
                start_line=1,
                end_line=total_lines,
            )
        )
    return chunks


def chunk_code(text: str, ext: str, source_path: str, start_index: int = 0) -> list[Chunk]:
    language = language_for_extension(ext)
    def_types = _DEFINITION_TYPES.get(language) if language else None
    if not language or not def_types:
        return _fallback_chunks(text, source_path, start_index)

    try:
        parser = get_parser(language)
    except Exception:
        return _fallback_chunks(text, source_path, start_index)

    src = text.encode("utf-8", errors="ignore")
    root = parser.parse(src).root_node

    chunks: list[Chunk] = []
    index = start_index
    buffer: list = []  # consecutive non-definition top-level nodes

    def flush_buffer() -> None:
        nonlocal index
        if not buffer:
            return
        start_byte, end_byte = buffer[0].start_byte, buffer[-1].end_byte
        snippet = src[start_byte:end_byte].decode("utf-8", errors="ignore").strip()
        if snippet:
            chunks.append(
                Chunk(
                    text=snippet,
                    chunk_index=index,
                    token_count=count_tokens(snippet),
                    source_path=source_path,
                    start_line=buffer[0].start_point[0] + 1,
                    end_line=buffer[-1].end_point[0] + 1,
                )
            )
            index += 1
        buffer.clear()

    for node in root.children:
        if node.type in def_types:
            flush_buffer()
            snippet = src[node.start_byte:node.end_byte].decode("utf-8", errors="ignore").strip()
            if not snippet:
                continue
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            if count_tokens(snippet) > _MAX_UNIT_TOKENS:
                for piece in _token_subchunks(snippet, 500, 60):
                    piece = piece.strip()
                    if not piece:
                        continue
                    chunks.append(
                        Chunk(
                            text=piece, chunk_index=index, token_count=count_tokens(piece),
                            source_path=source_path, start_line=start_line, end_line=end_line,
                        )
                    )
                    index += 1
            else:
                chunks.append(
                    Chunk(
                        text=snippet, chunk_index=index, token_count=count_tokens(snippet),
                        source_path=source_path, start_line=start_line, end_line=end_line,
                    )
                )
                index += 1
        else:
            buffer.append(node)

    flush_buffer()
    return chunks

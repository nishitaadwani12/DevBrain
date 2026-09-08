"""Parse uploaded documents into page/section-tagged text segments.

Each segment carries a ``page`` number (1-indexed for PDFs, else None) so that
downstream chunks can cite an exact location back to the source.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from pypdf import PdfReader
import docx
from markdown_it import MarkdownIt


@dataclass
class Segment:
    text: str
    page: int | None = None  # 1-indexed source page, when available


class UnsupportedFileType(Exception):
    pass


def _parse_pdf(data: bytes) -> list[Segment]:
    reader = PdfReader(io.BytesIO(data))
    segments: list[Segment] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            segments.append(Segment(text=text, page=i))
    return segments


def _parse_docx(data: bytes) -> list[Segment]:
    document = docx.Document(io.BytesIO(data))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    return [Segment(text=text)] if text else []


_md = MarkdownIt()


def _parse_markdown(data: bytes) -> list[Segment]:
    # Render to plain-ish text by stripping markdown tokens we don't need.
    text = data.decode("utf-8", errors="ignore").strip()
    return [Segment(text=text)] if text else []


def _parse_text(data: bytes) -> list[Segment]:
    text = data.decode("utf-8", errors="ignore").strip()
    return [Segment(text=text)] if text else []


_PARSERS = {
    "pdf": _parse_pdf,
    "docx": _parse_docx,
    "md": _parse_markdown,
    "markdown": _parse_markdown,
    "txt": _parse_text,
    "text": _parse_text,
}


SUPPORTED_EXTENSIONS = frozenset(_PARSERS)


def is_supported(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in SUPPORTED_EXTENSIONS


def parse_document(filename: str, data: bytes) -> list[Segment]:
    """Dispatch on file extension; return non-empty text segments."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    parser = _PARSERS.get(ext)
    if parser is None:
        raise UnsupportedFileType(f"Unsupported file type: .{ext}")
    return parser(data)

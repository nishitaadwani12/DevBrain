"""Token-aware chunking that preserves source location for citations."""
from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from app.services.parsing import Segment

# cl100k_base is a good general-purpose tokenizer for length estimation.
_encoder = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    text: str
    chunk_index: int
    page: int | None
    token_count: int


def _split_tokens(text: str, chunk_tokens: int, overlap: int) -> list[str]:
    tokens = _encoder.encode(text)
    if len(tokens) <= chunk_tokens:
        return [text]
    pieces: list[str] = []
    step = max(1, chunk_tokens - overlap)
    for start in range(0, len(tokens), step):
        window = tokens[start : start + chunk_tokens]
        if not window:
            break
        pieces.append(_encoder.decode(window))
        if start + chunk_tokens >= len(tokens):
            break
    return pieces


def chunk_segments(
    segments: list[Segment],
    chunk_tokens: int = 500,
    overlap: int = 60,
) -> list[Chunk]:
    """Chunk each segment independently so page attribution is preserved."""
    chunks: list[Chunk] = []
    index = 0
    for segment in segments:
        for piece in _split_tokens(segment.text, chunk_tokens, overlap):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(
                Chunk(
                    text=piece,
                    chunk_index=index,
                    page=segment.page,
                    token_count=len(_encoder.encode(piece)),
                )
            )
            index += 1
    return chunks

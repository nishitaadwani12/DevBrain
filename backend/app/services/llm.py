"""Gemini chat wrapper with streaming support (google-genai SDK)."""
from __future__ import annotations

from collections.abc import Iterator

from app.core.config import get_settings
from app.services.embeddings import _client  # reuse the configured client


def stream_answer(prompt: str) -> Iterator[str]:
    """Yield answer text incrementally as Gemini generates it."""
    settings = get_settings()
    stream = _client().models.generate_content_stream(
        model=settings.chat_model,
        contents=prompt,
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text


def generate_answer(prompt: str) -> str:
    """Non-streaming variant (used where a single response is simpler)."""
    settings = get_settings()
    resp = _client().models.generate_content(
        model=settings.chat_model,
        contents=prompt,
    )
    return resp.text or ""

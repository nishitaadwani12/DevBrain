"""Gemini embeddings wrapper (google-genai SDK).

Uses distinct task types for documents vs. queries, which improves retrieval
quality with the text-embedding-004 model.
"""
from __future__ import annotations

from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import get_settings


@lru_cache
def _client() -> genai.Client:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=settings.gemini_api_key)


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed passages for storage."""
    settings = get_settings()
    resp = _client().models.embed_content(
        model=settings.embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=settings.embedding_dim,
        ),
    )
    return [e.values for e in resp.embeddings]


def embed_query(text: str) -> list[float]:
    """Embed a single search query."""
    settings = get_settings()
    resp = _client().models.embed_content(
        model=settings.embedding_model,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=settings.embedding_dim,
        ),
    )
    return resp.embeddings[0].values

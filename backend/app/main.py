"""DevBrain FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agent,
    chat,
    conversations,
    documents,
    repos,
    search,
    suggestions,
    workspaces,
)
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(title="DevBrain API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspaces.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(repos.router)
app.include_router(conversations.router)
app.include_router(agent.router)
app.include_router(suggestions.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {
        "status": "ok",
        "gemini_configured": bool(settings.gemini_api_key),
        "db_configured": bool(settings.database_url),
    }

"""Authentication dependency backed by Supabase.

Verifies the caller's access token by calling Supabase's ``/auth/v1/user``
endpoint. This works regardless of Supabase's token signing method (legacy
HS256 or the newer asymmetric keys) and needs only the project URL + anon key.

For local single-user development, set ``AUTH_ENABLED=false`` to bypass token
checks and attribute all data to ``DEV_USER_ID``.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)


@dataclass
class User:
    id: str
    email: str | None = None


def _verify_with_supabase(token: str) -> User:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(500, "Supabase auth is not configured")
    try:
        resp = httpx.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_anon_key},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(503, f"Auth service unreachable: {exc}") from exc

    if resp.status_code != 200:
        raise HTTPException(401, "Invalid or expired token")

    data = resp.json()
    user_id = data.get("id")
    if not user_id:
        raise HTTPException(401, "Token did not resolve to a user")
    return User(id=user_id, email=data.get("email"))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    settings = get_settings()
    if not settings.auth_enabled:
        return User(id=settings.dev_user_id)
    if credentials is None:
        raise HTTPException(401, "Missing bearer token")
    return _verify_with_supabase(credentials.credentials)

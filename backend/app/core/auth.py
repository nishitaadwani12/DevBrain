"""Authentication dependency backed by Supabase JWTs.

Supabase issues an HS256 JWT (signed with the project JWT secret) on login. We
verify it here and expose the user id (``sub``) to route handlers.

For local single-user development, set ``AUTH_ENABLED=false`` to bypass token
checks and attribute all data to ``DEV_USER_ID``.
"""
from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)


@dataclass
class User:
    id: str
    email: str | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    settings = get_settings()

    if not settings.auth_enabled:
        return User(id=settings.dev_user_id)

    if credentials is None:
        raise HTTPException(401, "Missing bearer token")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(401, f"Invalid token: {exc}") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Token missing subject")
    return User(id=user_id, email=payload.get("email"))

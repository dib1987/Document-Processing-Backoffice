"""
Clerk JWT Authentication Middleware — DocFlow AI

Verifies Clerk JWTs on every request and injects:
  request.state.org_id   — the organization UUID (from our DB)
  request.state.user_id  — the user UUID (from our DB)
  request.state.role     — "admin" | "reviewer" | "viewer"
  request.state.clerk_user_id — raw Clerk user ID

Returns 401 if the token is missing or invalid.
Returns 403 if the user's role doesn't meet the endpoint's requirement.

Role hierarchy:
  admin    — full access
  reviewer — can upload, review, approve/reject
  viewer   — read-only (dashboard, audit trail, client list)
"""
import logging
from functools import wraps
from typing import Callable

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from models.db_models import User

logger = logging.getLogger(__name__)
settings = get_settings()

bearer_scheme = HTTPBearer(auto_error=False)

# Clerk's JWKS endpoint — used to fetch public keys for JWT verification
CLERK_JWKS_URL = "https://api.clerk.com/v1/jwks"

_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                CLERK_JWKS_URL,
                headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            )
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


async def _verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk JWT and return its claims.
    Raises HTTPException(401) on failure.
    """
    try:
        # Decode header to get key ID
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        jwks = await _get_jwks()
        public_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                public_key = key
                break

        if not public_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown JWT key")

        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return claims
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency. Verifies the JWT and returns the User ORM object.
    Injects org_id, user_id, role into request.state for downstream use.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = await _verify_clerk_token(credentials.credentials)
    clerk_user_id = claims.get("sub")

    if not clerk_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    user = await session.scalar(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please complete registration.",
        )

    # Inject into request state for convenient access in routers
    request.state.org_id = user.org_id
    request.state.user_id = user.id
    request.state.role = user.role
    request.state.clerk_user_id = clerk_user_id

    return user


# ──────────────────────────────────────────────
# Role enforcement dependencies
# ──────────────────────────────────────────────

ROLE_HIERARCHY = {"viewer": 0, "reviewer": 1, "admin": 2}


def require_role(minimum_role: str):
    """
    FastAPI dependency factory.
    Usage: Depends(require_role("admin"))
    """
    async def _check(user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(user.role, -1)
        required_level = ROLE_HIERARCHY.get(minimum_role, 999)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the '{minimum_role}' role or higher.",
            )
        return user
    return _check


# Convenience aliases
require_viewer   = Depends(require_role("viewer"))
require_reviewer = Depends(require_role("reviewer"))
require_admin    = Depends(require_role("admin"))

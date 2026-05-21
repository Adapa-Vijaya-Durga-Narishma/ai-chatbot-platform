"""
FastAPI authentication dependency.
Reads JWT from httpOnly cookie and returns the authenticated User.
"""
from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token, get_user_by_id


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate the httpOnly JWT cookie and return the authenticated User.
    Raises 401 if token is missing, expired, or invalid.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "not_authenticated", "message": "Not authenticated"},
        )
    try:
        user_id = decode_access_token(access_token)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Invalid or expired token"},
        )

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "user_not_found", "message": "User no longer exists"},
        )
    return user

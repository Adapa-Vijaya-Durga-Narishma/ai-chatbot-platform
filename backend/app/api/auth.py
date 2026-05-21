"""
Auth API router - HTTP layer only, no business logic.
POST /register, POST /login, POST /logout, GET /me
GET /google/login, GET /google/callback
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.auth_service import (
    create_access_token,
    get_google_oauth_login_url,
    google_login,
    login_user,
    register_user,
)

router = APIRouter()

_COOKIE_NAME = "access_token"
_COOKIE_OPTS = {
    "key": _COOKIE_NAME,
    "httponly": True,
    "samesite": "lax",
    "secure": settings.ENVIRONMENT != "development",
    "max_age": settings.JWT_EXPIRE_MINUTES * 60,
}


def _frontend_base_url() -> str:
    origins = settings.get_cors_origins()
    return origins[0] if origins else "http://localhost:5173"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        user = await register_user(db, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "conflict", "message": str(exc)},
        )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
async def login(
    payload: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        user = await login_user(db, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": str(exc)},
        )
    token = create_access_token(user.id)
    response.set_cookie(value=token, **_COOKIE_OPTS)
    return UserResponse.model_validate(user)


@router.get("/google/login")
async def google_login_redirect() -> RedirectResponse:
    try:
        url = get_google_oauth_login_url()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "oauth_config", "message": str(exc)},
        )
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        user = await google_login(db, code)
    except Exception:
        frontend_error_url = f"{_frontend_base_url()}/?auth_error=google_login_failed"
        return RedirectResponse(url=frontend_error_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    token = create_access_token(user.id)
    response = RedirectResponse(url=_frontend_base_url(), status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    response.set_cookie(value=token, **_COOKIE_OPTS)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(_COOKIE_NAME)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)

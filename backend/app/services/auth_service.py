"""
Auth service — all business logic for registration, login, and JWT.
No FastAPI imports here; framework-agnostic and fully unit-testable.
"""
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import bcrypt
import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.models.user import User


def _get_google_oauth_config() -> tuple[str, str | None, str]:
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    redirect_uri = settings.GOOGLE_REDIRECT_URI

    # Fallback for stale process config: re-read from .env at call time.
    if not client_id or not redirect_uri:
        refreshed = Settings()
        client_id = refreshed.GOOGLE_CLIENT_ID
        client_secret = refreshed.GOOGLE_CLIENT_SECRET
        redirect_uri = refreshed.GOOGLE_REDIRECT_URI

    if not client_id:
        raise ValueError("Google OAuth is not configured")
    return client_id, client_secret, redirect_uri


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    if len(plain.encode("utf-8")) > 72:
        raise ValueError("Password cannot exceed 72 bytes")
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> uuid.UUID:
    """Decode JWT and return user_id UUID. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    sub = payload.get("sub")
    if not sub:
        raise JWTError("Missing subject")
    return uuid.UUID(sub)


# ── Service functions ─────────────────────────────────────────────────────────

async def register_user(db: AsyncSession, email: str, password: str) -> User:
    """Create a new user. Raises ValueError if email already exists."""
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ValueError("Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login_user(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials. Raises ValueError on bad email/password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password:
        raise ValueError("Invalid email or password")
    if not verify_password(password, user.hashed_password):
        raise ValueError("Invalid email or password")
    return user


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def get_google_oauth_login_url() -> str:
    client_id, _, redirect_uri = _get_google_oauth_config()

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def google_login(db: AsyncSession, code: str) -> User:
    client_id, client_secret, redirect_uri = _get_google_oauth_config()
    if not client_secret:
        raise ValueError("Google OAuth is not configured")

    token_payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data=token_payload,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()

        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Google token exchange failed")

        profile_resp = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()

    email = profile.get("email")
    google_id = profile.get("sub")
    if not email or not google_id:
        raise ValueError("Google profile is missing required fields")

    user_by_google = await db.execute(select(User).where(User.google_id == google_id))
    existing_google_user = user_by_google.scalar_one_or_none()
    if existing_google_user:
        return existing_google_user

    user_by_email = await db.execute(select(User).where(User.email == email))
    existing_email_user = user_by_email.scalar_one_or_none()
    if existing_email_user:
        existing_email_user.google_id = google_id
        await db.commit()
        await db.refresh(existing_email_user)
        return existing_email_user

    new_user = User(
        id=uuid.uuid4(),
        email=email,
        google_id=google_id,
        hashed_password=None,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

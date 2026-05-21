"""
SQLAlchemy async session factory and engine.

Import `get_db` as a FastAPI dependency in route handlers.
Import `engine` in Alembic env.py for migrations.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _build_db_url() -> str:
    """Ensure DATABASE_URL uses asyncpg driver."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _build_db_url(),
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        yield session

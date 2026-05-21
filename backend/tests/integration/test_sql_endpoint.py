"""Integration test for SQL chat endpoint."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from main import app
from app.db.session import get_db
from app.core.auth import get_current_user


@pytest.mark.asyncio
async def test_sql_chat_endpoint_strips_trailing_semicolons(
    db: AsyncSession, current_user: User
) -> None:
    """Test that the SQL endpoint accepts queries with trailing semicolons."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Override the dependencies to use test user and db
        async def override_get_db():
            yield db

        async def override_get_current_user():
            return current_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        response = await client.post(
            "/api/sql-chat/query",
            json={"question": "How many users are there"},
        )

        # Should NOT return 400 "Multiple SQL statements are not allowed"
        assert response.status_code != 400, f"Unexpected 400 error: {response.text}"
        
        # Should return 200 or 422 (if query fails) but not 400 for semicolon
        assert response.status_code in (200, 422, 502), f"Unexpected status: {response.status_code}, body: {response.text}"

        app.dependency_overrides.clear()

"""SQLDatabase helpers for PostgreSQL + LangChain SQL tooling."""
from langchain_community.utilities import SQLDatabase

from app.core.config import settings


class GuardedSQLDatabase(SQLDatabase):
    """SQLDatabase wrapper that blocks unsafe SQL before any execution."""

    def run(self, command: str, *args, **kwargs):  # type: ignore[override]
        from app.services.sql_guard_service import validate_read_only_sql

        validate_read_only_sql(command, settings.sql_allowed_tables)
        return super().run(command, *args, **kwargs)

    def run_no_throw(self, command: str, *args, **kwargs):  # type: ignore[override]
        from app.services.sql_guard_service import validate_read_only_sql

        validate_read_only_sql(command, settings.sql_allowed_tables)
        return super().run_no_throw(command, *args, **kwargs)


def _build_sync_db_url() -> str:
    """Convert asyncpg URL to psycopg2 URL for LangChain SQLDatabase."""
    url = settings.DATABASE_URL.strip()

    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url

    raise ValueError("DATABASE_URL must be a PostgreSQL URL")


def get_sql_database(allowed_tables: list[str] | None = None) -> SQLDatabase:
    """Create a guarded SQLDatabase instance limited to configured tables."""
    include_tables = [table.strip() for table in (allowed_tables or []) if table.strip()] or None

    return GuardedSQLDatabase.from_uri(
        database_uri=_build_sync_db_url(),
        include_tables=include_tables,
        sample_rows_in_table_info=2,
    )

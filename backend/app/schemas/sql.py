"""Pydantic schemas for SQL chat API."""
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SQLChatQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    thread_id: UUID | None = None


class SQLChatQueryResponse(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    answer: str
    explanation: str | None = None
    summary: str | None = None
    thread_id: UUID | None = None

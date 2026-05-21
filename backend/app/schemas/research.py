"""Schemas for research digest requests."""
import uuid

from pydantic import BaseModel, Field


class ResearchDigestRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=400)
    thread_id: uuid.UUID | None = None

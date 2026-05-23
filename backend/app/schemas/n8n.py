"""Pydantic schemas for n8n sidecar endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class N8NResearchDigestRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=400)
    user_email: str = Field(
        default="n8n-automation@amzur.com",
        description="Email used for LiteLLM usage tracking.",
    )


class N8NResearchDigestResponse(BaseModel):
    digest_id: uuid.UUID
    topic: str
    digest: str
    paper_count: int
    iterations_used: int
    run_at: datetime


class N8NHealthResponse(BaseModel):
    status: str
    message: str

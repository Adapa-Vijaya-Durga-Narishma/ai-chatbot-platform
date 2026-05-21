"""
Chat Pydantic schemas — separate from ORM models.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.attachment import AttachmentResponse


# ── Chat request / streaming response ────────────────────────────────────────

class ChatRequest(BaseModel):
    """User message sent to the chatbot."""
    message: str = Field(..., min_length=1, max_length=5000)
    thread_id: uuid.UUID | None = None  # None → create new thread
    attachment_ids: list[uuid.UUID] | None = None
    mode: str = Field(default="normal", pattern="^(normal|upload|upload-pdf|generate-image)$")


class ChatResponse(BaseModel):
    """Single streaming chunk from the chatbot."""
    content: str
    finished: bool = False


# ── Thread ────────────────────────────────────────────────────────────────────

class ChatThreadResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatThreadCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ChatThreadUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


# ── Message ───────────────────────────────────────────────────────────────────

class ChatMessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    attachments: list[AttachmentResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ImageGenerationChatResponse(BaseModel):
    thread_id: uuid.UUID
    message: ChatMessageResponse

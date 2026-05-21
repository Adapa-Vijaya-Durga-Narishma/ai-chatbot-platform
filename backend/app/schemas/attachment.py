"""
Attachment schemas.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID | None
    original_filename: str
    stored_filename: str
    file_path: str
    mime_type: str
    file_size: int
    attachment_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AttachmentUploadResponse(BaseModel):
    attachments: list[AttachmentResponse]

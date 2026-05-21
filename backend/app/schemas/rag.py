"""
RAG-related API schemas.
"""
import uuid

from pydantic import BaseModel

from app.schemas.attachment import AttachmentResponse


class PdfUploadResponse(BaseModel):
    thread_id: uuid.UUID
    attachment: AttachmentResponse
    chunks_indexed: int
    status: str

"""
Service utilities for AI image generation in chat.
"""
from __future__ import annotations

import uuid
from pathlib import Path
import re

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.chains.image_generation import generate_image_base64
from app.core.config import settings
from app.models.attachment import Attachment
from app.models.chat import ChatMessage

IMAGE_TRIGGER_PATTERNS = [
    re.compile(r"\bgenerate\b.*\bimage\b", re.IGNORECASE),
    re.compile(r"\bcreate\b.*\bimage\b", re.IGNORECASE),
    re.compile(r"\bdraw\b", re.IGNORECASE),
    re.compile(r"\bmake\b.*\bimage\b", re.IGNORECASE),
]

PROMPT_PREFIX_PATTERNS = [
    re.compile(r"^\s*generate\s+(an?\s+)?image\s+(of|for)?\s*", re.IGNORECASE),
    re.compile(r"^\s*create\s+(an?\s+)?image\s+(of|for)?\s*", re.IGNORECASE),
    re.compile(r"^\s*make\s+(an?\s+)?image\s+(of|for)?\s*", re.IGNORECASE),
    re.compile(r"^\s*draw\s+(me\s+)?(an?\s+)?\s*", re.IGNORECASE),
]


def is_image_generation_prompt(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in IMAGE_TRIGGER_PATTERNS)


def extract_image_prompt(message: str) -> str:
    text = " ".join((message or "").strip().split())
    if not text:
        return ""

    extracted = text
    for pattern in PROMPT_PREFIX_PATTERNS:
        extracted = pattern.sub("", extracted, count=1)

    return extracted.strip(" .,!?:;\"'")


def _generated_images_dir() -> Path:
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    target_dir = (upload_root / "generated-images").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if upload_root not in target_dir.parents and upload_root != target_dir:
        raise ValueError("Invalid upload directory")

    return target_dir


def _extension_for_mime(mime_type: str) -> str:
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/gif":
        return ".gif"
    if mime_type == "image/webp":
        return ".webp"
    if mime_type == "image/bmp":
        return ".bmp"
    return ".png"


async def create_generated_image_message(
    db: AsyncSession,
    thread_id: uuid.UUID,
    user_email: str,
    prompt: str,
) -> ChatMessage:
    clean_prompt = " ".join(prompt.strip().split())
    if not clean_prompt:
        raise ValueError("Please provide a description for the image you want to generate")

    image_bytes, mime_type = generate_image_base64(clean_prompt, user_email)
    if not mime_type.startswith("image/"):
        raise ValueError("Generated output is not a valid image")

    output_dir = _generated_images_dir()
    extension = _extension_for_mime(mime_type)
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    file_path_abs = (output_dir / stored_filename).resolve()

    upload_root = Path(settings.UPLOAD_DIR).resolve()
    if upload_root not in file_path_abs.parents:
        raise ValueError("Invalid output path")

    async with aiofiles.open(file_path_abs, "wb") as output_file:
        await output_file.write(image_bytes)

    relative_file_path = file_path_abs.relative_to(upload_root).as_posix()
    db_file_path = f"{settings.UPLOAD_DIR.rstrip('/')}" + f"/{relative_file_path}"

    assistant_message = ChatMessage(
        id=uuid.uuid4(),
        thread_id=thread_id,
        role="assistant",
        content=f'Here is your generated image for: "{clean_prompt}"',
    )
    db.add(assistant_message)
    await db.flush()

    attachment = Attachment(
        id=uuid.uuid4(),
        message_id=assistant_message.id,
        original_filename=f"generated-{assistant_message.id}{extension}",
        stored_filename=stored_filename,
        file_path=db_file_path,
        mime_type=mime_type,
        file_size=len(image_bytes),
        attachment_type="generated_image",
    )
    db.add(attachment)
    await db.commit()

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.id == assistant_message.id)
        .options(selectinload(ChatMessage.attachments))
    )
    message_with_attachments = result.scalar_one_or_none()
    if message_with_attachments is None:
        raise ValueError("Failed to load generated image message")

    return message_with_attachments


__all__ = [
    "create_generated_image_message",
    "extract_image_prompt",
    "is_image_generation_prompt",
]

"""
AI image generation utilities.

All calls go through the centralized OpenAI SDK client configured in app.ai.llm
which points to the LiteLLM proxy.
"""
from __future__ import annotations

import base64

from openai import OpenAIError

from app.ai.llm import openai_client
from app.core.config import settings


def generate_image_base64(prompt: str, user_email: str) -> tuple[bytes, str]:
    """
    Generate an image and return raw image bytes + inferred mime type.

    Raises:
        ValueError: if prompt or image payload is invalid.
        OpenAIError: if provider/proxy call fails.
    """
    normalized_prompt = " ".join(prompt.strip().split())
    if not normalized_prompt:
        raise ValueError("Image prompt cannot be empty")

    response = openai_client.images.generate(
        model=settings.IMAGE_GEN_MODEL,
        prompt=normalized_prompt,
        user=user_email,
        timeout=90,
        extra_body={
            "metadata": {
                "application": settings.APP_NAME,
                "environment": settings.ENVIRONMENT,
            }
        },
    )

    data_items = getattr(response, "data", None) or []
    if not data_items:
        raise ValueError("Image provider returned an empty response")

    first_item = data_items[0]
    b64_payload = getattr(first_item, "b64_json", None)
    if not b64_payload:
        raise ValueError("Image provider did not return base64 image data")

    try:
        image_bytes = base64.b64decode(b64_payload, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid image payload returned by provider") from exc

    if not image_bytes:
        raise ValueError("Image payload was empty")

    mime_type = "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
    elif image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        mime_type = "image/gif"
    elif image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        mime_type = "image/webp"
    elif image_bytes.startswith(b"BM"):
        mime_type = "image/bmp"

    return image_bytes, mime_type

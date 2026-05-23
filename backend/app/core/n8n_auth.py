"""API key authentication dependency for n8n sidecar endpoints.

n8n cannot use httpOnly cookies. Instead, it sends X-N8N-API-Key header.
The value must match N8N_API_KEY in .env. If N8N_API_KEY is not set,
the endpoint rejects all requests so it is never accidentally open.
"""
from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_n8n_api_key(x_n8n_api_key: str | None = Header(default=None)) -> None:
    """Dependency — validates the n8n shared API key from the request header."""
    if not settings.N8N_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "n8n_not_configured",
                "message": "N8N_API_KEY is not configured on this server.",
            },
        )
    if x_n8n_api_key != settings.N8N_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_api_key",
                "message": "Invalid or missing X-N8N-API-Key header.",
            },
        )

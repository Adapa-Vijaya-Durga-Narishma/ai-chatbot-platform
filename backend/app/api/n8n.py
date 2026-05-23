"""n8n sidecar API router.

All endpoints here are protected by X-N8N-API-Key header authentication
(see app.core.n8n_auth). They are NOT protected by the httpOnly JWT cookie
because n8n cannot send cookies.

Registered under /api/n8n in main.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.n8n_auth import require_n8n_api_key
from app.db.session import get_db
from app.schemas.n8n import N8NHealthResponse, N8NResearchDigestRequest, N8NResearchDigestResponse
from app.services.n8n_research_service import run_research_digest_sync

router = APIRouter()


@router.get(
    "/health",
    response_model=N8NHealthResponse,
    dependencies=[Depends(require_n8n_api_key)],
)
async def n8n_health() -> N8NHealthResponse:
    """Health check for n8n to confirm the sidecar endpoint is reachable."""
    return N8NHealthResponse(status="ok", message="n8n sidecar is reachable.")


@router.post(
    "/research-digest",
    response_model=N8NResearchDigestResponse,
    dependencies=[Depends(require_n8n_api_key)],
)
async def research_digest_sync(
    request: N8NResearchDigestRequest,
    db: AsyncSession = Depends(get_db),
) -> N8NResearchDigestResponse:
    """Run the research agent for a topic and return the full digest as JSON.

    Called by n8n's HTTP Request node. Runs synchronously (no SSE streaming)
    so n8n can read the response directly. Persists result to research_digests
    table for audit history.

    Headers required:
        X-N8N-API-Key: <N8N_API_KEY from .env>

    Body:
        topic (str): research topic to digest
        user_email (str): email for LiteLLM usage tracking (optional)
    """
    try:
        result = await run_research_digest_sync(
            db=db,
            topic=request.topic,
            user_email=request.user_email,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_request", "message": str(exc)},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "research_failure", "message": str(exc)},
        )

    return result

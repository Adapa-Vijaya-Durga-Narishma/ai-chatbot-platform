"""Research digest API router (HTTP-only layer)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.research import ResearchDigestRequest
from app.services.research_service import stream_research_digest

router = APIRouter()


@router.post("/research-digest", response_model=None)
async def research_digest(
    request: ResearchDigestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    try:
        stream = stream_research_digest(
            db=db,
            current_user=current_user,
            topic=request.topic,
            thread_id=request.thread_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_request", "message": str(exc)},
        )

    return StreamingResponse(stream, media_type="text/event-stream")

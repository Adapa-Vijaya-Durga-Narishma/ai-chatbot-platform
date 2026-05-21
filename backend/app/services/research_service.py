"""Service layer for autonomous research digest streaming."""
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.research_agent import ResearchDigestAgent
from app.models.chat import ChatThread
from app.models.user import User
from app.services.chat_service import create_thread, save_message


def _format_sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=True)}\n\n"


def _thread_title_from_topic(topic: str) -> str:
    compressed = " ".join(topic.split())
    if len(compressed) <= 80:
        return compressed
    return compressed[:77].rstrip() + "..."


async def _resolve_or_create_thread(
    db: AsyncSession,
    current_user: User,
    thread_id: uuid.UUID | None,
    topic: str,
) -> ChatThread:
    if thread_id:
        result = await db.execute(
            select(ChatThread).where(
                ChatThread.id == thread_id,
                ChatThread.user_id == current_user.id,
            )
        )
        thread = result.scalar_one_or_none()
        if thread:
            return thread

    return await create_thread(
        db=db,
        user_id=current_user.id,
        title=f"Research: {_thread_title_from_topic(topic)}",
    )


async def stream_research_digest(
    db: AsyncSession,
    current_user: User,
    topic: str,
    thread_id: uuid.UUID | None = None,
) -> AsyncGenerator[str, None]:
    """Run research digest flow and stream progress + final sections as SSE."""
    cleaned_topic = " ".join(topic.split())
    if not cleaned_topic:
        yield _format_sse(
            {
                "type": "error",
                "error": "invalid_request",
                "message": "Research topic is required.",
            }
        )
        return

    thread = await _resolve_or_create_thread(db, current_user, thread_id, cleaned_topic)

    await save_message(
        db=db,
        thread_id=thread.id,
        role="user",
        content=f"Research request: {cleaned_topic}",
    )

    yield _format_sse({"type": "thread", "thread_id": str(thread.id)})

    agent = ResearchDigestAgent()
    final_digest = ""

    try:
        async for event in agent.stream_research(cleaned_topic, current_user.email):
            if event.get("type") == "done":
                final_digest = str(event.get("digest", "")).strip()
            yield _format_sse(event)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        yield _format_sse(
            {
                "type": "error",
                "error": "research_failure",
                "message": str(exc),
            }
        )
        return

    if final_digest:
        await save_message(
            db=db,
            thread_id=thread.id,
            role="assistant",
            content=final_digest,
        )

    yield _format_sse({"type": "complete", "thread_id": str(thread.id)})

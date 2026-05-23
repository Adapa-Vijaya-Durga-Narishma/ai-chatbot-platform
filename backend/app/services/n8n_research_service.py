"""Service layer for n8n sidecar research digest (synchronous, non-streaming).

This service runs the same ResearchDigestAgent used by the chat SSE endpoint,
but waits for full completion and returns a plain dict — no streaming.
n8n's HTTP Request node reads the JSON response directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.research_agent import ResearchDigestAgent
from app.models.research import ResearchDigest
from app.schemas.n8n import N8NResearchDigestResponse


async def run_research_digest_sync(
    db: AsyncSession,
    topic: str,
    user_email: str,
) -> N8NResearchDigestResponse:
    """Run the research agent synchronously and persist the digest.

    Collects all streamed events from ResearchDigestAgent, extracts the
    final digest text, saves it to research_digests, and returns a
    JSON-serialisable response ready for n8n.
    """
    cleaned_topic = " ".join(topic.split())

    agent = ResearchDigestAgent()

    final_digest = ""
    paper_count = 0
    iterations_used = 0

    async for event in agent.stream_research(cleaned_topic, user_email):
        if event.get("type") == "done":
            final_digest = str(event.get("digest", "")).strip()
            paper_count = int(event.get("paper_count", 0))
            iterations_used = int(event.get("iterations_used", 0))

    if not final_digest:
        final_digest = f"No digest could be generated for topic: {cleaned_topic}"

    digest_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)

    record = ResearchDigest(
        id=digest_id,
        topic=cleaned_topic,
        digest=final_digest,
        paper_count=paper_count,
        iterations_used=iterations_used,
        email_sent=False,
        run_at=now,
        created_at=now,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return N8NResearchDigestResponse(
        digest_id=record.id,
        topic=record.topic,
        digest=record.digest,
        paper_count=record.paper_count,
        iterations_used=record.iterations_used,
        run_at=record.run_at,
    )


async def mark_digest_email_sent(db: AsyncSession, digest_id: uuid.UUID) -> None:
    """Mark a digest record as having had its email sent.

    Called by the n8n router after n8n confirms email delivery,
    keeping the audit trail accurate.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(ResearchDigest).where(ResearchDigest.id == digest_id)
    )
    record = result.scalar_one_or_none()
    if record:
        record.email_sent = True
        await db.commit()

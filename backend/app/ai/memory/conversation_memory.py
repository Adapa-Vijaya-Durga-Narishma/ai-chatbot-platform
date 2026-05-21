"""
Conversation memory utilities.
Fetches recent thread-scoped history from the database for prompt context.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatThread


def _role_label(role: str) -> str:
    if role == "user":
        return "User"
    if role == "assistant":
        return "Assistant"
    return role.capitalize()


async def get_recent_messages(
    db: AsyncSession,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 5,
    exclude_message_id: uuid.UUID | None = None,
) -> str:
    """
    Load the most recent messages for a user-owned thread.

    Query order is DESC for efficiency, then reversed in Python to return
    chronological order (oldest -> newest) for LLM context.
    """
    stmt = (
        select(ChatMessage.role, ChatMessage.content)
        .join(ChatThread, ChatThread.id == ChatMessage.thread_id)
        .where(
            ChatMessage.thread_id == thread_id,
            ChatThread.user_id == user_id,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )

    if exclude_message_id is not None:
        stmt = stmt.where(ChatMessage.id != exclude_message_id)

    rows = (await db.execute(stmt)).all()
    if not rows:
        return ""

    chronological_rows = list(reversed(rows))
    formatted_lines = [
        f"{_role_label(role)}: {content.strip()}"
        for role, content in chronological_rows
    ]
    return "\n".join(formatted_lines)

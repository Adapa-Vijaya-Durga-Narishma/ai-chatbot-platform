"""SQL chat API router (HTTP layer only)."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.chat import ChatThread
from app.schemas.sql import SQLChatQueryRequest, SQLChatQueryResponse
from app.services.sql_chat_service import (
    SQLQueryExecutionError,
    SQLQueryGenerationError,
    ask_sql_question,
)
from app.services.sql_guard_service import SQLGuardError
from app.services.chat_service import save_message

router = APIRouter()


async def _ensure_sql_thread(
    db: AsyncSession,
    current_user: User,
    thread_id: uuid.UUID | None,
) -> uuid.UUID | None:
    if thread_id:
        return thread_id
    try:
        new_thread = ChatThread(
            id=uuid.uuid4(),
            user_id=current_user.id,
            title="Database Query",
        )
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
        return new_thread.id
    except Exception:
        return None


async def _persist_sql_exchange(
    db: AsyncSession,
    thread_id: uuid.UUID | None,
    question: str,
    assistant_content: str,
) -> None:
    if not thread_id:
        return
    try:
        await save_message(
            db=db,
            thread_id=thread_id,
            role="user",
            content=question,
        )
        await save_message(
            db=db,
            thread_id=thread_id,
            role="assistant",
            content=assistant_content,
        )
    except Exception:
        pass


def _build_sql_persisted_content(result: dict) -> str:
    sql_text = str(result.get("sql", "")).strip()
    answer = str(result.get("answer", "")).strip()
    summary = str(result.get("summary", "")).strip()
    explanation = str(result.get("explanation", "")).strip()
    rows = result.get("rows") if isinstance(result.get("rows"), list) else []

    lines = [f"SQL Query: ```sql\n{sql_text}\n```"]

    # Keep thread history readable: avoid persisting huge markdown tables.
    is_large_tabular_answer = (
        isinstance(answer, str)
        and ("\n|" in answer or answer.startswith("Found "))
        and len(rows) > 1
    )

    if is_large_tabular_answer:
        lines.append("")
        lines.append(f"Result Summary: {summary or f'Returned {len(rows)} rows.'}")
        preview = _build_rows_preview_markdown(rows, max_rows=len(rows), max_cell_len=80)
        if preview:
            lines.append("")
            lines.append("Preview:")
            lines.append(preview)
        lines.append("Open the SQL Results modal for the full table output.")
    else:
        lines.append("")
        lines.append(f"Result: {answer}")

    if explanation:
        lines.append("")
        lines.append(f"Explanation: {explanation}")

    if summary and not is_large_tabular_answer:
        lines.append("")
        lines.append(f"Summary: {summary}")

    return "\n".join(lines)


def _build_rows_preview_markdown(
    rows: list[dict],
    max_rows: int = 8,
    max_cell_len: int = 80,
) -> str:
    if not rows:
        return ""

    headers = list(rows[0].keys())
    if not headers:
        return ""

    visible_rows = rows[:max_rows]
    header = "| " + " | ".join(str(col) for col in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body_lines: list[str] = []

    for row in visible_rows:
        cells: list[str] = []
        for col in headers:
            cell = str(row.get(col, "") or "")
            cell = cell.replace("\n", " ").replace("|", "\\|")
            if len(cell) > max_cell_len:
                cell = cell[: max_cell_len - 3] + "..."
            cells.append(cell)
        body_lines.append("| " + " | ".join(cells) + " |")

    lines = [header, separator, *body_lines]
    if len(rows) > max_rows:
        lines.append(f"\nShowing {max_rows} of {len(rows)} rows.")

    return "\n".join(lines)


@router.post("/query", response_model=SQLChatQueryResponse)
async def query_sql_chat(
    request: SQLChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SQLChatQueryResponse:
    result = None
    thread_id = request.thread_id
    
    try:
        result = await ask_sql_question(
            db=db,
            current_user=current_user,
            question=request.question,
            thread_id=thread_id,
        )
    except SQLGuardError as exc:
        thread_id = await _ensure_sql_thread(db, current_user, thread_id)
        await _persist_sql_exchange(db, thread_id, request.question, str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "blocked_sql", "message": str(exc), "thread_id": str(thread_id) if thread_id else None},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_request", "message": str(exc)},
        )
    except SQLQueryGenerationError as exc:
        thread_id = await _ensure_sql_thread(db, current_user, thread_id)
        await _persist_sql_exchange(db, thread_id, request.question, str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "invalid_sql",
                "message": str(exc),
                "thread_id": str(thread_id) if thread_id else None,
            },
        )
    except SQLQueryExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "db_failure", "message": str(exc)},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "unexpected", "message": str(exc)},
        )

    thread_id = await _ensure_sql_thread(db, current_user, thread_id)
    sql_response_content = _build_sql_persisted_content(result)
    await _persist_sql_exchange(db, thread_id, request.question, sql_response_content)

    # Include thread_id in response
    result["thread_id"] = thread_id
    return SQLChatQueryResponse(**result)

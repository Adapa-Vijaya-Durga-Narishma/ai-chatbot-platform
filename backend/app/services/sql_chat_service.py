"""Business logic for natural-language-to-SQL chat."""
import asyncio
import uuid
from typing import Any
import re

from sqlalchemy import desc, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.sql_chain import extract_sql_query, invoke_sql_agent
from app.ai.sql.sql_database import get_sql_database
from app.core.config import settings
from app.models.chat import ChatMessage, ChatThread
from app.models.user import User
from app.services.sql_guard_service import (
    SQLGuardError,
    validate_read_only_intent,
    validate_read_only_sql,
)


SQL_TABLE_COLUMNS: dict[str, list[str]] = {
    "users": ["id", "email", "google_id", "created_at"],
    "chat_threads": ["id", "user_id", "title", "created_at"],
    "chat_messages": ["id", "thread_id", "role", "content", "created_at"],
    "attachments": [
        "id",
        "message_id",
        "original_filename",
        "stored_filename",
        "file_path",
        "mime_type",
        "file_size",
        "attachment_type",
        "created_at",
    ],
}

SQL_RELATIONSHIPS: dict[tuple[str, str], str] = {
    ("chat_threads", "users"): "chat_threads.user_id = users.id",
    ("chat_messages", "chat_threads"): "chat_messages.thread_id = chat_threads.id",
    ("attachments", "chat_messages"): "attachments.message_id = chat_messages.id",
}


class SQLQueryGenerationError(RuntimeError):
    """Raised when SQL generation fails or returns invalid output."""


class SQLQueryExecutionError(RuntimeError):
    """Raised when SQL execution fails."""


async def ask_sql_question(
    db: AsyncSession,
    current_user: User,
    question: str,
    thread_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Generate, validate, and execute a read-only SQL query from natural language."""
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Question is required")

    validate_read_only_intent(cleaned_question)

    normalized_question = cleaned_question.strip().lower()
    precomputed_sql: str | None = None
    if _is_table_count_question(normalized_question):
        precomputed_sql = _fallback_sql_from_question(cleaned_question, settings.sql_allowed_tables)

    contextual_question = await _build_contextual_question(
        db=db,
        user_id=getattr(current_user, "id", None),
        thread_id=thread_id,
        question=cleaned_question,
    )

    sql_database = get_sql_database(settings.sql_allowed_tables)

    agent_response = None
    if precomputed_sql is None:
        try:
            agent_response = await asyncio.to_thread(
                invoke_sql_agent,
                contextual_question,
                current_user.email,
                sql_database,
            )
        except Exception:  # pragma: no cover - network/provider dependent
            pass

    generated_sql = precomputed_sql
    if generated_sql is None and agent_response:
        generated_sql = extract_sql_query(agent_response)

    if not generated_sql:
        generated_sql = _fallback_sql_from_question(cleaned_question, settings.sql_allowed_tables)

    if not generated_sql:
        raise SQLQueryGenerationError(_build_clarification_message(cleaned_question, settings.sql_allowed_tables))

    used_fallback_sql = precomputed_sql is not None

    try:
        validated_sql = validate_read_only_sql(generated_sql, settings.sql_allowed_tables)
    except SQLGuardError as exc:
        fallback_sql = _fallback_sql_from_question(cleaned_question, settings.sql_allowed_tables)
        if not fallback_sql:
            if "not in the allowed table list" in str(exc).lower():
                raise SQLQueryGenerationError(
                    _build_allowed_tables_message(settings.sql_allowed_tables)
                ) from exc
            raise
        used_fallback_sql = True
        validated_sql = validate_read_only_sql(fallback_sql, settings.sql_allowed_tables)
    optimized_sql = _optimize_select_wildcard(validated_sql, settings.sql_allowed_tables)
    executable_sql = _ensure_limit(optimized_sql, settings.SQL_QUERY_MAX_ROWS)

    try:
        rows = await _execute_sql_query(db, executable_sql)
    except SQLQueryExecutionError:
        fallback_sql = _fallback_sql_from_question(cleaned_question, settings.sql_allowed_tables)
        if not fallback_sql:
            raise
        used_fallback_sql = True
        fallback_validated = validate_read_only_sql(fallback_sql, settings.sql_allowed_tables)
        fallback_optimized = _optimize_select_wildcard(fallback_validated, settings.sql_allowed_tables)
        fallback_executable = _ensure_limit(fallback_optimized, settings.SQL_QUERY_MAX_ROWS)
        if fallback_executable == executable_sql:
            raise
        executable_sql = fallback_executable
        rows = await _execute_sql_query(db, executable_sql)
    answer = _build_answer(
        None if used_fallback_sql else (agent_response.get("output") if agent_response else None),
        rows,
    )
    explanation = _build_explanation(executable_sql)
    summary = _build_summary(rows)

    return {
        "sql": executable_sql,
        "rows": rows,
        "answer": answer,
        "explanation": explanation,
        "summary": summary,
    }


async def _execute_sql_query(db: AsyncSession, sql: str) -> list[dict[str, Any]]:
    safe_sql, params = _parameterize_sql_literals(sql)
    try:
        result = await db.execute(text(safe_sql), params)
    except SQLAlchemyError as exc:
        await db.rollback()
        raise SQLQueryExecutionError("Database query execution failed") from exc

    mapped_rows = result.mappings().all()
    return [dict(row) for row in mapped_rows]


def _ensure_limit(sql: str, max_rows: int) -> str:
    if _is_aggregate_query(sql):
        return sql
    if re.search(r"\bLIMIT\b", sql, flags=re.IGNORECASE):
        return sql
    return f"{sql} LIMIT {max_rows}"


def _is_aggregate_query(sql: str) -> bool:
    return bool(re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", sql, flags=re.IGNORECASE))


def _optimize_select_wildcard(sql: str, allowed_tables: list[str]) -> str:
    if not re.search(r"^\s*SELECT\s+\*\s+FROM\s+", sql, flags=re.IGNORECASE):
        return sql
    if re.search(r"\bJOIN\b", sql, flags=re.IGNORECASE):
        return sql

    match = re.match(r"^\s*SELECT\s+\*\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_\.]*)", sql, flags=re.IGNORECASE)
    if not match:
        return sql

    table_ref = match.group(1)
    table_name = table_ref.split(".")[-1].strip().strip('"').lower()
    allowed = {t.strip().lower() for t in allowed_tables if t.strip()}
    columns = SQL_TABLE_COLUMNS.get(table_name)
    if table_name not in allowed or not columns:
        return sql

    projection = ", ".join(columns)
    return re.sub(r"^\s*SELECT\s+\*", f"SELECT {projection}", sql, count=1, flags=re.IGNORECASE)


def _parameterize_sql_literals(sql: str) -> tuple[str, dict[str, Any]]:
    params: dict[str, Any] = {}
    index = 0

    def replacer(match: re.Match[str]) -> str:
        nonlocal index
        start = match.start()
        prefix = sql[max(0, start - 20):start].lower()
        if re.search(r"interval\s*$", prefix):
            return match.group(0)

        key = f"p{index}"
        index += 1
        params[key] = match.group(1).replace("''", "'")
        return f":{key}"

    rewritten = re.sub(r"'((?:''|[^'])*)'", replacer, sql)
    return rewritten, params


async def _build_contextual_question(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    thread_id: uuid.UUID | None,
    question: str,
) -> str:
    if not user_id or not thread_id or not _is_follow_up_question(question):
        return question

    result = await db.execute(
        select(ChatMessage.content)
        .join(ChatThread, ChatMessage.thread_id == ChatThread.id)
        .where(
            ChatMessage.thread_id == thread_id,
            ChatThread.user_id == user_id,
            ChatMessage.role == "user",
        )
        .order_by(desc(ChatMessage.created_at))
        .limit(4)
    )
    prior_questions = [value for value in result.scalars().all() if value and value.strip()]
    if len(prior_questions) < 2:
        return question

    context_lines = list(reversed(prior_questions[1:]))
    context_text = "\n".join(f"- {line}" for line in context_lines)
    return (
        "Resolve this SQL follow-up using prior query context.\n"
        f"Previous questions:\n{context_text}\n"
        f"Current question: {question}"
    )


def _is_follow_up_question(question: str) -> bool:
    normalized = question.strip().lower()
    if not normalized:
        return False
    follow_up_markers = (
        "only",
        "also",
        "and",
        "now",
        "sort",
        "order",
        "filter",
        "created",
        "with",
        "without",
        "latest",
        "oldest",
        "top",
        "first",
        "next",
    )
    return len(normalized.split()) <= 8 or any(normalized.startswith(marker) for marker in follow_up_markers)


def _build_answer(agent_output: Any, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No matching records were found for your question."

    if len(rows) == 1 and len(rows[0]) == 1:
        key = next(iter(rows[0].keys())).lower()
        value = next(iter(rows[0].values()))
        if any(token in key for token in ("count", "total", "num", "tables")):
            return f"Current count is {value}."
        if key == "content":
            content = str(value) if value is not None else ""
            # Render as blockquote so stored message content isn't confused with
            # a new SQL execution or live markdown output.
            quoted = "\n".join(f"> {line}" for line in content.splitlines()) if content else "> *(empty)*"
            return f"**Stored message content:**\n\n{quoted}"
        return f"The result is {value}."

    if (
        isinstance(agent_output, str)
        and agent_output.strip()
        and not _is_ungrounded_answer(agent_output)
        and not _looks_like_sql_echo(agent_output)
    ):
        return agent_output.strip()

    # Format as markdown table so the chat thread displays actual records
    headers = list(rows[0].keys())
    header_row = " | ".join(str(h) for h in headers)
    separator = " | ".join("---" for _ in headers)
    data_rows = []
    for row in rows:
        cells = []
        for h in headers:
            val = row.get(h, "")
            cell_str = str(val) if val is not None else ""
            # Truncate very long cell values (e.g. message content)
            if len(cell_str) > 80:
                cell_str = cell_str[:77] + "..."
            cells.append(cell_str)
        data_rows.append(" | ".join(cells))

    table = f"| {header_row} |\n| {separator} |\n" + "\n".join(f"| {r} |" for r in data_rows)
    return f"Found {len(rows)} record(s):\n\n{table}"


def _fallback_sql_from_question(question: str, allowed_tables: list[str]) -> str | None:
    normalized_question = question.strip().lower()
    if not normalized_question:
        return None

    if _is_table_listing_question(normalized_question):
        table_names = [table.strip() for table in allowed_tables if table.strip()]
        if table_names:
            unions = " UNION ALL ".join(
                f"SELECT '{table}' AS table_name" for table in table_names
            )
            return unions

    advanced_sql = _build_advanced_fallback_sql(normalized_question, allowed_tables)
    if advanced_sql:
        return advanced_sql

    # Handle user identity lookups like: "What is the email for this user id <uuid>?"
    if "users" in allowed_tables and _is_user_email_lookup_question(normalized_question):
        user_id = _extract_uuid_from_text(normalized_question)
        if user_id:
            return f"SELECT email FROM users WHERE id = '{user_id}'"

    # Handle schema-level table count questions even when no specific table is named.
    if _is_table_count_question(normalized_question):
        table_count = len([table for table in allowed_tables if table.strip()])
        return f"SELECT {table_count} AS total_tables"

    matched_table = _match_table_from_question(normalized_question, allowed_tables)
    if not matched_table:
        return None

    if _is_id_lookup_question(normalized_question):
        record_id = _extract_uuid_from_text(normalized_question)
        if record_id:
            selected_columns = _columns_for_id_lookup(matched_table, normalized_question)
            return (
                f"SELECT {selected_columns} FROM {matched_table} "
                f"WHERE id = '{record_id}' LIMIT 1"
            )

    # Check for count-related patterns (more flexible matching)
    if any(phrase in normalized_question for phrase in ("how many", "count", "number of", "total", "how much", "how many ")):
        count_alias = _count_alias_for_table(matched_table)
        return f"SELECT COUNT(*) AS {count_alias} FROM {matched_table}"

    if any(phrase in normalized_question for phrase in ("latest", "recent", "newest", "last")):
        columns = ", ".join(SQL_TABLE_COLUMNS.get(matched_table, ["*"]))
        return f"SELECT {columns} FROM {matched_table} ORDER BY created_at DESC LIMIT 10"

    if _is_list_query(normalized_question):
        sql = _build_list_query_for_table(matched_table, normalized_question)
        if sql:
            return sql

    return None


def _match_table_from_question(question: str, allowed_tables: list[str]) -> str | None:
    # Prefer direct semantic phrases for core chat relations.
    if re.search(r"\bchat\s+messages?\b|\bmessages?\b", question):
        for table in allowed_tables:
            if table.strip().lower().endswith("messages"):
                return table.strip()

    if re.search(r"\bchat\s+threads?\b|\bthreads?\b", question):
        for table in allowed_tables:
            if table.strip().lower().endswith("threads"):
                return table.strip()

    # Stage 1: Try exact table name match (highest priority)
    for table in allowed_tables:
        table_name = table.strip()
        if not table_name:
            continue

        singular = table_name[:-1] if table_name.endswith("s") else table_name
        table_pattern = rf"\b{re.escape(table_name.lower())}\b"
        singular_pattern = rf"\b{re.escape(singular.lower())}\b"
        if re.search(table_pattern, question) or re.search(singular_pattern, question):
            return table_name

    # Stage 2: Component matching with scoring to prioritize specific matches
    # Avoid matching generic prefixes like "chat" in favor of specific table names
    matches = []
    
    for table in allowed_tables:
        table_name = table.strip()
        if not table_name:
            continue
        
        components = table_name.split("_")
        for i, component in enumerate(components):
            if component and len(component) > 2:  # Avoid short words
                component_pattern = rf"\b{re.escape(component.lower())}\b"
                if re.search(component_pattern, question):
                    # Score: non-generic components (e.g., "messages", "threads") rank higher
                    # Components that are "generic prefixes" (like "chat", "user") rank lower
                    is_generic = component.lower() in ("chat", "user", "app", "data")
                    score = 1 if not is_generic else 0
                    matches.append((score, table_name))
    
    # Return the highest-scoring match
    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[0][1]

    return None


def _count_alias_for_table(table_name: str) -> str:
    singular = table_name[:-1] if table_name.endswith("s") else table_name
    return f"total_{singular.lower()}"


def _is_table_count_question(question: str) -> bool:
    has_table_term = re.search(r"\btables?\b", question) is not None
    has_count_intent = any(
        phrase in question
        for phrase in ("how many", "count", "number of", "total")
    )
    return has_table_term and has_count_intent


def _is_table_listing_question(question: str) -> bool:
    has_table_term = (
        re.search(r"\btables\b", question) is not None
        or "table names" in question
    )
    has_listing_intent = any(
        phrase in question
        for phrase in (
            "show",
            "list",
            "give",
            "what are",
            "which",
            "available",
            "in database",
        )
    )
    return has_table_term and has_listing_intent and not _is_table_count_question(question)


def _is_user_email_lookup_question(question: str) -> bool:
    has_email = "email" in question
    has_user = "user" in question
    has_id = "id" in question
    return has_email and has_user and has_id


def _is_id_lookup_question(question: str) -> bool:
    has_id = "id" in question
    has_lookup_intent = any(token in question for token in ("give", "show", "get", "find", "content", "record"))
    return has_id and has_lookup_intent


def _columns_for_id_lookup(table_name: str, question: str) -> str:
    table = table_name.lower()
    if table == "chat_messages" and "content" in question:
        # Respect direct field requests like "give me the content of this id".
        requested: list[str] = []
        if "id" in question and any(token in question for token in ("with id", "include id", "show id")):
            requested.append("id")
        if "role" in question:
            requested.append("role")
        if "created" in question or "timestamp" in question or "time" in question:
            requested.append("created_at")
        requested.append("content")
        return ", ".join(dict.fromkeys(requested))
    columns = SQL_TABLE_COLUMNS.get(table_name)
    if columns:
        return ", ".join(columns)
    return "*"


def _is_list_query(question: str) -> bool:
    return any(token in question for token in ("list", "show", "all", "display", "fetch", "get"))


def _build_list_query_for_table(table_name: str, question: str) -> str:
    table = table_name.lower()

    if table == "chat_messages":
        base = "SELECT id, thread_id, role, content, created_at FROM chat_messages"
        if re.search(r"\buser\s+role\b|\brole\s+user\b|\brole\s*=\s*'?user'?\b", question):
            return base + " WHERE role = 'user' ORDER BY created_at DESC LIMIT 100"
        if re.search(r"\bassistant\s+role\b|\brole\s+assistant\b|\brole\s*=\s*'?assistant'?\b", question):
            return base + " WHERE role = 'assistant' ORDER BY created_at DESC LIMIT 100"
        return base + " ORDER BY created_at DESC LIMIT 100"

    if table == "chat_threads":
        return "SELECT id, user_id, title, created_at FROM chat_threads ORDER BY created_at DESC LIMIT 100"

    if table == "users":
        if "gmail" in question:
            return "SELECT id, email, google_id, created_at FROM users WHERE email ILIKE '%@gmail.com' ORDER BY created_at DESC LIMIT 100"
        if "google" in question:
            return "SELECT id, email, google_id, created_at FROM users WHERE google_id IS NOT NULL ORDER BY created_at DESC LIMIT 100"
        return "SELECT id, email, google_id, created_at FROM users ORDER BY created_at DESC LIMIT 100"

    if table == "attachments":
        size_match = re.search(r"larger than\s+(\d+)\s*mb", question)
        if size_match:
            mb = int(size_match.group(1))
            return (
                "SELECT id, message_id, original_filename, mime_type, file_size, attachment_type, created_at "
                f"FROM attachments WHERE file_size > {mb * 1024 * 1024} ORDER BY file_size DESC LIMIT 100"
            )
        if "pdf" in question:
            return (
                "SELECT id, message_id, original_filename, mime_type, file_size, attachment_type, created_at "
                "FROM attachments WHERE mime_type ILIKE 'application/pdf%' ORDER BY created_at DESC LIMIT 100"
            )
        return (
            "SELECT id, message_id, original_filename, mime_type, attachment_type, created_at "
            "FROM attachments ORDER BY created_at DESC LIMIT 100"
        )

    columns = ", ".join(SQL_TABLE_COLUMNS.get(table_name, ["*"]))
    return f"SELECT {columns} FROM {table_name} LIMIT 100"


def _build_advanced_fallback_sql(question: str, allowed_tables: list[str]) -> str | None:
    allowed = {table.strip().lower() for table in allowed_tables if table.strip()}

    if "threads" in question and "user" in question and "count" in question and "users" in allowed and "chat_threads" in allowed:
        return (
            "SELECT u.id, u.email, COUNT(t.id) AS thread_count "
            "FROM users u LEFT JOIN chat_threads t ON t.user_id = u.id "
            "GROUP BY u.id, u.email ORDER BY thread_count DESC LIMIT 100"
        )

    if "count" in question and "messages" in question and "role" in question and "chat_messages" in allowed:
        return (
            "SELECT role, COUNT(*) AS total_messages "
            "FROM chat_messages GROUP BY role ORDER BY total_messages DESC"
        )

    if "attachments" in question and "message" in question and "with" in question and "attachments" in allowed and "chat_messages" in allowed:
        return (
            "SELECT a.id, a.original_filename, a.attachment_type, a.created_at, m.id AS message_id, m.content "
            "FROM attachments a JOIN chat_messages m ON a.message_id = m.id "
            "ORDER BY a.created_at DESC LIMIT 100"
        )

    if "threads" in question and "without" in question and "messages" in question and "chat_threads" in allowed and "chat_messages" in allowed:
        return (
            "SELECT t.id, t.user_id, t.title, t.created_at "
            "FROM chat_threads t LEFT JOIN chat_messages m ON m.thread_id = t.id "
            "WHERE m.id IS NULL ORDER BY t.created_at DESC LIMIT 100"
        )

    if "users" in question and "without" in question and "threads" in question and "users" in allowed and "chat_threads" in allowed:
        return (
            "SELECT u.id, u.email, u.google_id, u.created_at "
            "FROM users u LEFT JOIN chat_threads t ON t.user_id = u.id "
            "WHERE t.id IS NULL ORDER BY u.created_at DESC LIMIT 100"
        )

    if "messages" in question and "without" in question and "attachments" in question and "chat_messages" in allowed and "attachments" in allowed:
        return (
            "SELECT m.id, m.thread_id, m.role, m.content, m.created_at "
            "FROM chat_messages m LEFT JOIN attachments a ON a.message_id = m.id "
            "WHERE a.id IS NULL ORDER BY m.created_at DESC LIMIT 100"
        )

    if "average" in question and "attachment" in question and "size" in question and "attachments" in allowed:
        return "SELECT AVG(file_size) AS average_attachment_size_bytes FROM attachments"

    if "largest" in question and "attachment" in question and "attachments" in allowed:
        return (
            "SELECT id, message_id, original_filename, file_size, mime_type, created_at "
            "FROM attachments ORDER BY file_size DESC LIMIT 1"
        )

    date_sql = _build_date_filter_sql(question, allowed)
    if date_sql:
        return date_sql

    return None


def _build_date_filter_sql(question: str, allowed: set[str]) -> str | None:
    if "users" in question and "users" in allowed:
        if "today" in question:
            return "SELECT id, email, google_id, created_at FROM users WHERE created_at >= CURRENT_DATE ORDER BY created_at DESC LIMIT 100"
        if "yesterday" in question:
            return (
                "SELECT id, email, google_id, created_at FROM users "
                "WHERE created_at >= CURRENT_DATE - INTERVAL '1 day' AND created_at < CURRENT_DATE "
                "ORDER BY created_at DESC LIMIT 100"
            )
        if "this month" in question:
            return (
                "SELECT id, email, google_id, created_at FROM users "
                "WHERE created_at >= date_trunc('month', NOW()) ORDER BY created_at DESC LIMIT 100"
            )

    if "messages" in question and "chat_messages" in allowed:
        days_match = re.search(r"last\s+(\d+)\s+days", question)
        if days_match:
            days = int(days_match.group(1))
            return (
                "SELECT id, thread_id, role, content, created_at FROM chat_messages "
                f"WHERE created_at >= NOW() - INTERVAL '{days} days' ORDER BY created_at DESC LIMIT 100"
            )
        if "today" in question:
            return "SELECT id, thread_id, role, content, created_at FROM chat_messages WHERE created_at >= CURRENT_DATE ORDER BY created_at DESC LIMIT 100"

    if "attachment" in question and "attachments" in allowed:
        if "today" in question or "latest uploaded" in question:
            return (
                "SELECT id, message_id, original_filename, mime_type, file_size, attachment_type, created_at "
                "FROM attachments WHERE created_at >= CURRENT_DATE ORDER BY created_at DESC LIMIT 100"
            )

    return None


def _build_explanation(sql: str) -> str:
    features: list[str] = []
    normalized = sql.lower()
    if " join " in normalized:
        features.append("joined related tables using foreign-key relationships")
    if " where " in normalized:
        features.append("applied filters from your question")
    if " ilike " in normalized:
        features.append("used case-insensitive text search")
    if " group by " in normalized:
        features.append("computed grouped aggregates")
    if any(fn in normalized for fn in ("count(", "avg(", "sum(", "min(", "max(")):
        features.append("used aggregate functions")
    if " order by " in normalized:
        features.append("applied sorting")
    if " limit " in normalized:
        features.append("limited the result size")

    if not features:
        return "Generated a read-only PostgreSQL query aligned to your request."
    return "Generated a read-only PostgreSQL query that " + ", ".join(features) + "."


def _build_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No matching rows were found."
    if len(rows) == 1:
        return "Returned 1 row."
    return f"Returned {len(rows)} rows."


def _extract_uuid_from_text(text: str) -> str | None:
    match = re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(0)


def _is_ungrounded_answer(answer: str) -> bool:
    normalized = answer.strip().lower()
    blocked_phrases = (
        "i don't have access",
        "i do not have access",
        "don't have access",
        "do not have access",
        "i can't tell you",
        "cannot tell you",
        "i'm sorry",
        "im sorry",
        "as an ai assistant",
        "i cannot access",
        "if you tell me what kind of database",
    )
    return any(phrase in normalized for phrase in blocked_phrases)


def _looks_like_sql_echo(answer: str) -> bool:
    normalized = answer.strip().lower()
    return "```sql" in normalized or bool(re.search(r"\bselect\s+.+\s+from\b", normalized))


def _build_clarification_message(question: str, allowed_tables: list[str]) -> str:
    trimmed = question.strip()
    allowed = [table.strip() for table in allowed_tables if table.strip()]
    if not trimmed:
        return "Please provide a database question."

    examples = [
        "show first 10 users",
        "latest 5 messages",
        "threads with user emails",
        "count messages by role",
    ]
    table_list = ", ".join(allowed) if allowed else "configured tables"
    return (
        "Your request is a bit ambiguous, so I could not determine a safe SQL query. "
        f"Please mention the specific table or relation ({table_list}) and what you need "
        "(filter, count, latest, search, etc.). "
        f"Examples: {', '.join(examples)}."
    )


def _build_allowed_tables_message(allowed_tables: list[str]) -> str:
    table_names = [table.strip() for table in allowed_tables if table.strip()]
    listed = ", ".join(table_names) if table_names else "none"
    return (
        "I can only query the configured application tables. "
        f"Available tables are: {listed}. "
        "Please rephrase your question using one of these table names."
    )

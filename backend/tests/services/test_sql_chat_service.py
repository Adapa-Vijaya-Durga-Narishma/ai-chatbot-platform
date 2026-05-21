from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.services.sql_chat_service import (
    SQLQueryGenerationError,
    SQLQueryExecutionError,
    _build_answer,
    _execute_sql_query,
    ask_sql_question,
)
from app.services.sql_guard_service import SQLGuardError


class DummyAction:
    def __init__(self, tool_input: str):
        self.tool_input = tool_input
        self.log = ""


@pytest.mark.asyncio
async def test_ask_sql_question_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: {
            "output": "There are two users.",
            "intermediate_steps": [(DummyAction("SELECT id, email FROM users LIMIT 2"), "")],
        },
    )
    monkeypatch.setattr(
        "app.services.sql_chat_service._execute_sql_query",
        AsyncMock(return_value=[{"id": 1, "email": "a@example.com"}, {"id": 2, "email": "b@example.com"}]),
    )

    user = SimpleNamespace(email="user@example.com")
    result = await ask_sql_question(db=object(), current_user=user, question="List users")

    assert result["sql"].lower().startswith("select")
    assert len(result["rows"]) == 2
    assert result["answer"] == "There are two users."


@pytest.mark.asyncio
async def test_ask_sql_question_blocks_unsafe_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: {
            "output": "Attempted query.",
            "intermediate_steps": [(DummyAction("DROP TABLE users"), "")],
        },
    )

    user = SimpleNamespace(email="user@example.com")
    with pytest.raises(SQLGuardError):
        await ask_sql_question(db=object(), current_user=user, question="Delete users")


@pytest.mark.asyncio
async def test_ask_sql_question_blocks_destructive_intent_message() -> None:
    user = SimpleNamespace(email="user@example.com")
    with pytest.raises(SQLGuardError, match="Only SELECT queries are allowed"):
        await ask_sql_question(db=object(), current_user=user, question="drop table users")


@pytest.mark.asyncio
async def test_ask_sql_question_falls_back_for_count_question(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: {
            "output": "I don't have access to that information.",
            "intermediate_steps": [],
        },
    )
    monkeypatch.setattr(
        "app.services.sql_chat_service._execute_sql_query",
        AsyncMock(return_value=[{"total_user": 5}]),
    )

    user = SimpleNamespace(email="user@example.com")
    result = await ask_sql_question(
        db=object(),
        current_user=user,
        question="How many user are there currently?",
    )

    assert result["sql"].lower().startswith("select count(*) as total_user from users")
    assert result["answer"] == "Current count is 5."


@pytest.mark.asyncio
async def test_ask_sql_question_table_count_uses_deterministic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())

    def should_not_be_called(*args, **kwargs):
        raise AssertionError("invoke_sql_agent should not be called for table count questions")

    monkeypatch.setattr("app.services.sql_chat_service.invoke_sql_agent", should_not_be_called)
    monkeypatch.setattr(
        "app.services.sql_chat_service._execute_sql_query",
        AsyncMock(return_value=[{"total_tables": 4}]),
    )

    user = SimpleNamespace(email="user@example.com")
    result = await ask_sql_question(
        db=object(),
        current_user=user,
        question="how many tables are in database?",
    )

    assert result["sql"].lower() == "select 4 as total_tables limit 100"
    assert result["answer"] == "Current count is 4."


@pytest.mark.asyncio
async def test_ask_sql_question_ignores_ungrounded_agent_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: {
            "output": "I'm sorry, I do not have access to that information.",
            "intermediate_steps": [(DummyAction("SELECT COUNT(*) AS total_user FROM users"), "")],
        },
    )
    monkeypatch.setattr(
        "app.services.sql_chat_service._execute_sql_query",
        AsyncMock(return_value=[{"total_user": 7}]),
    )

    user = SimpleNamespace(email="user@example.com")
    result = await ask_sql_question(db=object(), current_user=user, question="How many users?")

    assert result["answer"] == "Current count is 7."


@pytest.mark.asyncio
async def test_ask_sql_question_agent_exception_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: (_ for _ in ()).throw(Exception("Agent failed")),
    )
    monkeypatch.setattr(
        "app.services.sql_chat_service._execute_sql_query",
        AsyncMock(return_value=[{"total_user": 5}]),
    )

    user = SimpleNamespace(email="user@example.com")
    result = await ask_sql_question(
        db=object(),
        current_user=user,
        question="How many users are there in db?",
    )

    assert "count(*) as total_user from users" in result["sql"].lower()
    assert result["answer"] == "Current count is 5."


@pytest.mark.asyncio
async def test_ask_sql_question_falls_back_when_agent_sql_is_multi_statement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: {
            "output": "I found the table count.",
            "intermediate_steps": [(DummyAction("SELECT 4 AS total_tables; SELECT 5 AS total_tables"), "")],
        },
    )
    monkeypatch.setattr(
        "app.services.sql_chat_service._execute_sql_query",
        AsyncMock(return_value=[{"total_tables": 4}]),
    )

    user = SimpleNamespace(email="user@example.com")
    result = await ask_sql_question(
        db=object(),
        current_user=user,
        question="how many tables are in database?",
    )

    assert "select 4 as total_tables" in result["sql"].lower()
    assert result["answer"] == "Current count is 4."


@pytest.mark.asyncio
async def test_ask_sql_question_retries_with_fallback_on_execution_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: {
            "output": "Found email.",
            "intermediate_steps": [
                (DummyAction("SELECT email FROM users WHERE id = 1f6147c7-ca97-4bfe-8aba-7ab8814f75b1"), "")
            ],
        },
    )

    async def execute_side_effect(_db: object, sql: str):
        if "id = 1f6147c7-ca97-4bfe-8aba-7ab8814f75b1" in sql:
            raise Exception("bad uuid literal")
        return [{"email": "user@example.com"}]

    # Wrap side effect to raise service-specific execution error on malformed SQL only.
    async def wrapped_execute(_db: object, sql: str):
        try:
            return await execute_side_effect(_db, sql)
        except Exception as exc:  # pragma: no cover - behavior under test
            from app.services.sql_chat_service import SQLQueryExecutionError

            raise SQLQueryExecutionError("Database query execution failed") from exc

    monkeypatch.setattr("app.services.sql_chat_service._execute_sql_query", wrapped_execute)

    user = SimpleNamespace(email="user@example.com")
    result = await ask_sql_question(
        db=object(),
        current_user=user,
        question="What is the email for this user id 1f6147c7-ca97-4bfe-8aba-7ab8814f75b1?",
    )

    assert "select email from users where id = '1f6147c7-ca97-4bfe-8aba-7ab8814f75b1'" in result["sql"].lower()
    assert result["answer"] == "The result is user@example.com."


@pytest.mark.asyncio
async def test_ask_sql_question_retries_with_fallback_for_chat_message_content_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: {
            "output": "Found message content.",
            "intermediate_steps": [
                (
                    DummyAction(
                        "SELECT content FROM chat_messages WHERE id = 6d88cf18-9d04-4ef3-baad-c44d7b5d7de1"
                    ),
                    "",
                )
            ],
        },
    )

    async def execute_side_effect(_db: object, sql: str):
        if "id = 6d88cf18-9d04-4ef3-baad-c44d7b5d7de1" in sql:
            raise Exception("bad uuid literal")
        return [{"content": "hello from db"}]

    async def wrapped_execute(_db: object, sql: str):
        try:
            return await execute_side_effect(_db, sql)
        except Exception as exc:  # pragma: no cover - behavior under test
            from app.services.sql_chat_service import SQLQueryExecutionError

            raise SQLQueryExecutionError("Database query execution failed") from exc

    monkeypatch.setattr("app.services.sql_chat_service._execute_sql_query", wrapped_execute)

    user = SimpleNamespace(email="user@example.com")
    result = await ask_sql_question(
        db=object(),
        current_user=user,
        question="give me the content of this id 6d88cf18-9d04-4ef3-baad-c44d7b5d7de1 from chat messages table",
    )

    assert (
        "select content from chat_messages where id = '6d88cf18-9d04-4ef3-baad-c44d7b5d7de1' limit 1"
        in result["sql"].lower()
    )
    assert "Stored message content:" in result["answer"]
    assert "> hello from db" in result["answer"]


@pytest.mark.asyncio
async def test_execute_sql_query_rolls_back_on_error() -> None:
    db = AsyncMock()
    db.execute.side_effect = SQLAlchemyError("bad query")

    with pytest.raises(SQLQueryExecutionError):
        await _execute_sql_query(db, "SELECT email FROM users")

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_ask_sql_question_returns_clarification_for_ambiguous_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: {"output": "", "intermediate_steps": []},
    )

    user = SimpleNamespace(email="user@example.com")
    with pytest.raises(SQLQueryGenerationError, match="ambiguous"):
        await ask_sql_question(
            db=object(),
            current_user=user,
            question="Give me records in a table",
        )


@pytest.mark.asyncio
async def test_ask_sql_question_returns_allowed_tables_message_for_disallowed_table_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.sql_chat_service.get_sql_database", lambda _tables: object())
    monkeypatch.setattr(
        "app.services.sql_chat_service.invoke_sql_agent",
        lambda question, user_email, sql_db: {
            "output": "I can query it.",
            "intermediate_steps": [(DummyAction("SELECT * FROM payments"), "")],
        },
    )

    user = SimpleNamespace(email="user@example.com")
    with pytest.raises(SQLQueryGenerationError, match="Available tables are"):
        await ask_sql_question(
            db=object(),
            current_user=user,
            question="show payment table rows",
        )


def test_build_answer_ignores_sql_echo_output_for_multi_row_results() -> None:
    rows = [
        {
            "id": "1",
            "thread_id": "t1",
            "role": "assistant",
            "content": "hello",
            "created_at": "2026-05-15 11:01:45",
        },
        {
            "id": "2",
            "thread_id": "t1",
            "role": "assistant",
            "content": "how can I help?",
            "created_at": "2026-05-15 11:02:10",
        },
    ]
    agent_output = (
        "Here are the chat messages with the assistant role:\n\n"
        "```sql\nSELECT * FROM chat_messages WHERE role = 'assistant' LIMIT 10;\n```"
    )

    answer = _build_answer(agent_output, rows)

    assert "| id | thread_id | role | content | created_at |" in answer
    assert "role = 'assistant'" not in answer

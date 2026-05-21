"""Test that fallback SQL generation doesn't produce trailing semicolons."""
from app.services.sql_chat_service import _fallback_sql_from_question


def test_fallback_sql_no_semicolon_count_query() -> None:
    """Fallback SQL for count questions should not have trailing semicolon."""
    sql = _fallback_sql_from_question("How many users are there", ["users"])
    assert sql is not None
    assert not sql.endswith(";"), f"SQL should not end with semicolon: {sql}"
    assert "COUNT(*)" in sql


def test_fallback_sql_no_semicolon_latest_query() -> None:
    """Fallback SQL for latest questions should not have trailing semicolon."""
    sql = _fallback_sql_from_question("Show the latest orders", ["orders"])
    assert sql is not None
    assert not sql.endswith(";"), f"SQL should not end with semicolon: {sql}"
    assert "ORDER BY" in sql


def test_fallback_sql_matches_allowed_table() -> None:
    """Fallback SQL should use the allowed table name."""
    sql = _fallback_sql_from_question("How many customers", ["customers"])
    assert sql is not None
    assert "customers" in sql.lower()
    assert not sql.endswith(";")


def test_fallback_sql_matches_partial_table_name() -> None:
    """Fallback SQL should match partial table names like 'threads' to 'chat_threads'."""
    sql = _fallback_sql_from_question("Threads count?", ["users", "chat_threads", "chat_messages"])
    assert sql is not None
    assert "chat_threads" in sql
    assert "COUNT(*)" in sql
    assert not sql.endswith(";")


def test_fallback_sql_matches_messages_table() -> None:
    """Fallback SQL should match 'messages' to 'chat_messages' table, not generic 'chat' to 'chat_threads'."""
    sql = _fallback_sql_from_question("How many messages?", ["users", "chat_threads", "chat_messages"])
    assert sql is not None
    assert "chat_messages" in sql
    assert "chat_threads" not in sql
    assert "COUNT(*)" in sql


def test_fallback_sql_chat_messages_count() -> None:
    """Fallback SQL should correctly match 'Chat messages count?' to 'chat_messages' table."""
    sql = _fallback_sql_from_question("Chat messages count?", ["users", "chat_threads", "chat_messages"])
    assert sql is not None
    assert "chat_messages" in sql, f"Expected chat_messages in SQL: {sql}"
    assert "chat_threads" not in sql, f"Should not match chat_threads: {sql}"
    assert "COUNT(*)" in sql
    assert not sql.endswith(";")


def test_fallback_sql_counts_allowed_tables_for_schema_question() -> None:
    """Fallback SQL should answer schema-level table count questions."""
    sql = _fallback_sql_from_question(
        "How many tables are there?",
        ["users", "chat_threads", "chat_messages"],
    )
    assert sql is not None
    assert "SELECT 3 AS total_tables" in sql
    assert not sql.endswith(";")


def test_fallback_sql_user_email_by_uuid() -> None:
    """Fallback SQL should resolve email lookup by user UUID."""
    sql = _fallback_sql_from_question(
        "What is the email for this user id 1f6147c7-ca97-4bfe-8aba-7ab8814f75b1?",
        ["users", "chat_threads", "chat_messages"],
    )
    assert sql is not None
    assert "SELECT email FROM users WHERE id = '1f6147c7-ca97-4bfe-8aba-7ab8814f75b1'" in sql
    assert not sql.endswith(";")


def test_fallback_sql_chat_message_content_by_uuid() -> None:
    sql = _fallback_sql_from_question(
        "give me the content of this id 6d88cf18-9d04-4ef3-baad-c44d7b5d7de1 from chat messages table",
        ["users", "chat_threads", "chat_messages", "attachments"],
    )
    assert sql is not None
    assert "SELECT content FROM chat_messages" in sql
    assert "WHERE id = '6d88cf18-9d04-4ef3-baad-c44d7b5d7de1'" in sql
    assert not sql.endswith(";")


def test_fallback_sql_list_chat_messages() -> None:
    """Fallback SQL should support list/show/all queries for chat_messages."""
    sql = _fallback_sql_from_question(
        "List all the chat messages",
        ["users", "chat_threads", "chat_messages", "attachments"],
    )
    assert sql is not None
    assert "FROM chat_messages" in sql
    assert "ORDER BY created_at DESC" in sql
    assert not sql.endswith(";")


def test_fallback_sql_list_chat_messages_with_user_role() -> None:
    """Fallback SQL should filter chat_messages by role when user role is requested."""
    sql = _fallback_sql_from_question(
        "List all the chat messages with the user role",
        ["users", "chat_threads", "chat_messages", "attachments"],
    )
    assert sql is not None
    assert "FROM chat_messages" in sql
    assert "WHERE role = 'user'" in sql
    assert not sql.endswith(";")


def test_fallback_sql_list_tables_in_database() -> None:
    sql = _fallback_sql_from_question(
        "give me tables in the database",
        ["users", "chat_threads", "chat_messages", "attachments"],
    )
    assert sql is not None
    assert "SELECT 'users' AS table_name" in sql
    assert "UNION ALL" in sql


def test_fallback_sql_list_gmail_users() -> None:
    sql = _fallback_sql_from_question(
        "List gmail users",
        ["users", "chat_threads", "chat_messages", "attachments"],
    )
    assert sql is not None
    assert "FROM users" in sql
    assert "email ILIKE '%@gmail.com'" in sql


def test_fallback_sql_count_messages_by_role() -> None:
    sql = _fallback_sql_from_question(
        "Count messages by role",
        ["users", "chat_threads", "chat_messages", "attachments"],
    )
    assert sql is not None
    assert "FROM chat_messages" in sql
    assert "GROUP BY role" in sql


def test_fallback_sql_users_without_threads() -> None:
    sql = _fallback_sql_from_question(
        "Show users without threads",
        ["users", "chat_threads", "chat_messages", "attachments"],
    )
    assert sql is not None
    assert "LEFT JOIN chat_threads" in sql
    assert "WHERE t.id IS NULL" in sql

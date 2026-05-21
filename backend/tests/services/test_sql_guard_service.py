import pytest

from app.services.sql_guard_service import SQLGuardError, validate_read_only_sql


def test_blocks_dangerous_keywords_case_insensitive() -> None:
    with pytest.raises(SQLGuardError, match="Only SELECT queries are allowed"):
        validate_read_only_sql("SeLeCt * FrOm users DrOp table users", ["users"])


def test_blocks_multiple_statements() -> None:
    with pytest.raises(SQLGuardError):
        validate_read_only_sql("SELECT * FROM users; SELECT * FROM users", ["users"])


def test_blocks_tables_not_in_allowed_list() -> None:
    with pytest.raises(SQLGuardError):
        validate_read_only_sql("SELECT * FROM payments", ["users", "orders"])


def test_allows_safe_select_query() -> None:
    sql = validate_read_only_sql(
        "SELECT id, email FROM users WHERE email IS NOT NULL LIMIT 5",
        ["users"],
    )
    assert sql.startswith("SELECT")


def test_allows_single_statement_with_trailing_semicolon() -> None:
    sql = validate_read_only_sql("SELECT id, email FROM users;", ["users"])
    assert sql == "SELECT id, email FROM users"


def test_blocks_execute_keyword() -> None:
    with pytest.raises(SQLGuardError, match="Only SELECT queries are allowed"):
        validate_read_only_sql("SELECT EXECUTE('dangerous')", ["users"])

"""Tests for SQL chain normalization and extraction."""
from app.ai.chains.sql_chain import _normalize_sql_candidate


def test_normalize_strips_trailing_semicolon() -> None:
    """Ensure trailing semicolons are removed from SQL candidates."""
    result = _normalize_sql_candidate("SELECT * FROM users;")
    assert result == "SELECT * FROM users"
    assert ";" not in result


def test_normalize_removes_code_fences() -> None:
    """Ensure markdown code fences are removed."""
    result = _normalize_sql_candidate("```sql\nSELECT * FROM users\n```")
    assert result == "SELECT * FROM users"
    assert "```" not in result


def test_normalize_collapses_whitespace() -> None:
    """Ensure multiple whitespace is collapsed to single spaces."""
    result = _normalize_sql_candidate("SELECT  *  FROM   users")
    assert result == "SELECT * FROM users"


def test_normalize_with_multiple_issues() -> None:
    """Test normalization with semicolon, fences, and extra whitespace."""
    result = _normalize_sql_candidate("```sql\nSELECT  *  FROM  users ;\n```")
    assert result == "SELECT * FROM users"
    assert ";" not in result
    assert "```" not in result


def test_normalize_returns_none_for_empty() -> None:
    """Ensure None is returned for empty/invalid SQL."""
    assert _normalize_sql_candidate("") is None
    assert _normalize_sql_candidate("```") is None
    assert _normalize_sql_candidate("some random text") is None

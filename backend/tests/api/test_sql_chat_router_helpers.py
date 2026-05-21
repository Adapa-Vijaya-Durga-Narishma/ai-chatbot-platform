from app.api.sql_chat import _build_sql_persisted_content


def test_build_sql_persisted_content_compacts_large_tabular_answers() -> None:
    rows = [
        {"id": str(i), "role": "assistant" if i % 2 else "user"}
        for i in range(1, 12)
    ]
    content = _build_sql_persisted_content(
        {
            "sql": "SELECT id, role FROM chat_messages LIMIT 100",
            "rows": rows,
            "answer": "Found 11 record(s):\n\n| id | role |\n| --- | --- |\n...",
            "summary": "Returned 11 rows.",
            "explanation": "Generated a read-only PostgreSQL query.",
        }
    )

    assert "Result Summary: Returned 11 rows." in content
    assert "Preview:" in content
    assert "| id | role |" in content
    assert "| 11 | assistant |" in content
    assert "Showing 8 of 11 rows." not in content
    assert "Open the SQL Results modal for the full table output." in content


def test_build_sql_persisted_content_keeps_scalar_answers() -> None:
    content = _build_sql_persisted_content(
        {
            "sql": "SELECT 4 AS total_tables LIMIT 100",
            "rows": [{"total_tables": 4}],
            "answer": "Current count is 4.",
            "summary": "Returned 1 row.",
            "explanation": "Generated a read-only PostgreSQL query.",
        }
    )

    assert "Result: Current count is 4." in content
    assert "Summary: Returned 1 row." in content

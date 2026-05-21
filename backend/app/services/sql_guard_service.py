"""Safety guardrails for generated SQL queries."""
import re


BLOCKED_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER")
ADDITIONAL_BLOCKED_KEYWORDS = ("CREATE", "GRANT", "REVOKE", "COMMENT", "VACUUM", "EXECUTE")

READ_ONLY_VALIDATION_MESSAGE = (
    "Only SELECT queries are allowed. Destructive statements like "
    "INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE, GRANT, "
    "REVOKE, COMMENT, VACUUM, and EXECUTE are blocked."
)


class SQLGuardError(ValueError):
    """Raised when generated SQL violates read-only policy."""


def validate_read_only_intent(question: str) -> None:
    """Block destructive DB intents at question level before SQL generation."""
    normalized_question = question.strip()
    if not normalized_question:
        return

    blocked_pattern = r"\b(" + "|".join(BLOCKED_KEYWORDS + ADDITIONAL_BLOCKED_KEYWORDS) + r")\b"
    if re.search(blocked_pattern, normalized_question, flags=re.IGNORECASE):
        raise SQLGuardError(READ_ONLY_VALIDATION_MESSAGE)


def validate_read_only_sql(sql: str, allowed_tables: list[str] | None = None) -> str:
    """Validate SQL is a single read-only statement against allowed tables only."""
    normalized_sql = sql.strip()
    if not normalized_sql:
        raise SQLGuardError("Generated SQL is empty")

    # Allow a single trailing semicolon from model output, but still block
    # any internal semicolons that indicate multiple statements.
    normalized_sql = normalized_sql.rstrip(";").strip()

    if ";" in normalized_sql:
        raise SQLGuardError("Multiple SQL statements are not allowed")

    if "--" in normalized_sql or "/*" in normalized_sql or "*/" in normalized_sql:
        raise SQLGuardError("SQL comments are not allowed")

    if not re.match(r"^(SELECT|WITH)\b", normalized_sql, flags=re.IGNORECASE):
        raise SQLGuardError(READ_ONLY_VALIDATION_MESSAGE)

    blocked_pattern = r"\b(" + "|".join(BLOCKED_KEYWORDS + ADDITIONAL_BLOCKED_KEYWORDS) + r")\b"
    if re.search(blocked_pattern, normalized_sql, flags=re.IGNORECASE):
        raise SQLGuardError(READ_ONLY_VALIDATION_MESSAGE)

    if re.search(r"\bINTO\s+OUTFILE\b", normalized_sql, flags=re.IGNORECASE):
        raise SQLGuardError("Generated SQL contains blocked export syntax")

    if allowed_tables:
        _validate_allowed_tables(normalized_sql, allowed_tables)

    return normalized_sql


def _validate_allowed_tables(sql: str, allowed_tables: list[str]) -> None:
    allowed = {table.strip().lower() for table in allowed_tables if table.strip()}
    if not allowed:
        raise SQLGuardError("No allowed SQL tables are configured")

    # Basic table extraction from FROM/JOIN clauses.
    referenced = re.findall(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)", sql, flags=re.IGNORECASE)
    for table_ref in referenced:
        table_name = table_ref.split(".")[-1].strip().strip('"').lower()
        if table_name and table_name not in allowed:
            raise SQLGuardError(f"Table '{table_name}' is not in the allowed table list")

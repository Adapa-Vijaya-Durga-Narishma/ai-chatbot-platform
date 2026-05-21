"""LangChain SQL agent tooling for NL-to-SQL generation."""
from pathlib import Path
from typing import Any
import re

from langchain_community.agent_toolkits import SQLDatabaseToolkit, create_sql_agent
from langchain_community.utilities import SQLDatabase

from app.ai.llm import llm
from app.core.config import settings

prompt_path = Path(__file__).parent.parent / "prompts" / "sql_prompt.txt"
with open(prompt_path, encoding="utf-8") as f:
    sql_prompt_text = f.read()


def get_sql_agent_executor(sql_database: SQLDatabase):
    """Build a SQL agent with intermediate steps enabled for query extraction."""
    toolkit = SQLDatabaseToolkit(db=sql_database, llm=llm)
    return create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        prefix=sql_prompt_text,
        agent_type="tool-calling",
        verbose=settings.ENVIRONMENT == "development",
        max_iterations=6,
        return_intermediate_steps=True,
    )


def invoke_sql_agent(question: str, user_email: str, sql_database: SQLDatabase) -> dict[str, Any]:
    """Invoke SQL agent with user metadata required for LiteLLM tracking."""
    agent = get_sql_agent_executor(sql_database)
    return agent.invoke(
        {"input": question},
        config={"metadata": {"user_email": user_email}},
    )


def extract_sql_query(agent_response: dict[str, Any]) -> str | None:
    """Extract generated SQL from agent intermediate steps."""
    steps = agent_response.get("intermediate_steps") or []
    candidates: list[str] = []

    for step in steps:
        if not isinstance(step, (tuple, list)) or not step:
            continue

        action = step[0]
        observation = step[1] if len(step) > 1 else ""

        tool_input = getattr(action, "tool_input", None)
        if isinstance(tool_input, str):
            candidates.append(tool_input)
        elif isinstance(tool_input, dict):
            for key in ("query", "sql", "input"):
                value = tool_input.get(key)
                if isinstance(value, str):
                    candidates.append(value)

        log_text = getattr(action, "log", None)
        if isinstance(log_text, str):
            candidates.append(log_text)

        if isinstance(observation, str):
            candidates.append(observation)

    for text in reversed(candidates):
        cleaned = _normalize_sql_candidate(text)
        if cleaned:
            return cleaned

    output = agent_response.get("output")
    if isinstance(output, str):
        return _normalize_sql_candidate(output)

    return None


def _normalize_sql_candidate(text: str) -> str | None:
    without_fences = re.sub(r"```(?:sql)?|```", "", text, flags=re.IGNORECASE).strip()
    match = re.search(
        r"\b(SELECT|WITH|INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE)\b[\s\S]*",
        without_fences,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    sql = match.group(0).strip()
    sql = re.sub(r"\s+", " ", sql)
    sql = sql.rstrip(";").strip()
    return sql

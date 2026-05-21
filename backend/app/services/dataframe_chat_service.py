"""Service layer for dataframe-backed question answering."""
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pandas as pd
from pandas import DataFrame
from starlette.datastructures import UploadFile

from app.ai.agents.pandas_agent import invoke_pandas_agent

logger = logging.getLogger(__name__)
from app.services.dataframe_service import (
    DataframeLoadError,
    load_google_sheet_dataframe,
    load_uploaded_dataframe,
    summarize_dataframe,
)
from app.models.user import User


class DataframeSessionError(ValueError):
    """Raised when a user dataframe session is unavailable."""


class DataframeAgentError(RuntimeError):
    """Raised when dataframe agent execution fails."""


@dataclass
class UserDataframeSession:
    dataframe: DataFrame
    source_type: str
    source_name: str
    updated_at: datetime


_DATAFRAME_SESSIONS: dict[UUID, UserDataframeSession] = {}


async def store_uploaded_dataframe(current_user: User, file: UploadFile) -> dict[str, Any]:
    """Load and store an uploaded dataframe for a user."""
    dataframe = await load_uploaded_dataframe(file)
    source_name = file.filename or "uploaded-file"
    return _set_user_dataframe(current_user.id, dataframe, "upload", source_name)


def store_google_sheet_dataframe(current_user: User, sheet_url: str) -> dict[str, Any]:
    """Load and store a Google Sheet dataframe for a user."""
    dataframe = load_google_sheet_dataframe(sheet_url)
    return _set_user_dataframe(current_user.id, dataframe, "google-sheet", sheet_url)


async def ask_dataframe_question(current_user: User, question: str) -> dict[str, Any]:
    """Answer a natural-language question against the user's active dataframe."""
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Question is required")

    session = _DATAFRAME_SESSIONS.get(current_user.id)
    if session is None:
        raise DataframeSessionError("No dataframe is loaded for this user")

    # Prefer deterministic answers for simple structured queries to avoid LLM math errors.
    deterministic_answer = _deterministic_answer_from_dataframe(session.dataframe, cleaned_question)
    if deterministic_answer:
        summary = summarize_dataframe(session.dataframe)
        return {
            "answer": deterministic_answer,
            "source_type": session.source_type,
            "source_name": session.source_name,
            "row_count": summary["row_count"],
            "column_count": summary["column_count"],
            "columns": summary["columns"],
        }

    try:
        agent_response = invoke_pandas_agent(session.dataframe, cleaned_question, current_user.email)
    except Exception as exc:  # pragma: no cover - provider/runtime dependent
        logger.exception(f"Dataframe agent failed for user {current_user.email}: {exc}")
        raise DataframeAgentError("Failed to analyze dataframe") from exc

    answer = _extract_agent_answer(agent_response)
    if not answer:
        fallback_answer = _deterministic_answer_from_dataframe(session.dataframe, cleaned_question)
        if fallback_answer:
            answer = fallback_answer
        else:
            raise DataframeAgentError("The dataframe agent returned an empty response")

    summary = summarize_dataframe(session.dataframe)
    return {
        "answer": answer,
        "source_type": session.source_type,
        "source_name": session.source_name,
        "row_count": summary["row_count"],
        "column_count": summary["column_count"],
        "columns": summary["columns"],
    }


def _set_user_dataframe(
    user_id: UUID,
    dataframe: DataFrame,
    source_type: str,
    source_name: str,
) -> dict[str, Any]:
    _DATAFRAME_SESSIONS[user_id] = UserDataframeSession(
        dataframe=dataframe,
        source_type=source_type,
        source_name=source_name,
        updated_at=datetime.now(timezone.utc),
    )
    summary = summarize_dataframe(dataframe)
    return {
        "source_type": source_type,
        "source_name": source_name,
        "row_count": summary["row_count"],
        "column_count": summary["column_count"],
        "columns": summary["columns"],
        "preview_rows": summary["preview_rows"],
    }


def _extract_agent_answer(agent_response: Any) -> str:
    if isinstance(agent_response, dict):
        output = agent_response.get("output")
        if isinstance(output, str):
            return output.strip()
    if isinstance(agent_response, str):
        return agent_response.strip()
    return ""


def _deterministic_answer_from_dataframe(dataframe: DataFrame, question: str) -> str:
    """Return deterministic answers for common structured questions."""
    sum_answer = _sum_answer_from_dataframe(dataframe, question)
    if sum_answer:
        return sum_answer

    latest_version_answer = _latest_version_answer_from_dataframe(dataframe, question)
    if latest_version_answer:
        return latest_version_answer

    return ""


def _latest_version_answer_from_dataframe(dataframe: DataFrame, question: str) -> str:
    lowered_question = question.strip().lower()

    latest_version_match = re.search(r"latest\s+version\s+of\s+(.+)$", lowered_question)
    if not latest_version_match:
        return ""

    entity = latest_version_match.group(1).strip(" ?.")
    if not entity:
        return ""

    language_column = _find_column(dataframe, ["programming_language", "language", "name"])
    version_column = _find_column(dataframe, ["latest_version", "version", "current_version"])
    if not language_column or not version_column:
        return ""

    language_values = dataframe[language_column].astype(str).str.strip().str.lower()
    matched_rows = dataframe[language_values == entity]
    if matched_rows.empty:
        matched_rows = dataframe[language_values.str.contains(entity, na=False)]
    if matched_rows.empty:
        return ""

    latest_version = str(matched_rows.iloc[0][version_column]).strip()
    if not latest_version:
        return ""

    entity_title = entity.capitalize()
    return f"The latest version of {entity_title} is {latest_version}."


def _sum_answer_from_dataframe(dataframe: DataFrame, question: str) -> str:
    lowered_question = question.strip().lower()

    if " by " in lowered_question or "group" in lowered_question:
        return ""

    sum_match = re.search(r"\b(sum|total)\b.*?\b(of|for)\b\s+(.+)$", lowered_question)
    if not sum_match:
        return ""

    target_phrase = sum_match.group(3).strip(" ?.")
    target_phrase = re.sub(r"^the\s+", "", target_phrase)
    if not target_phrase:
        return ""

    column_name = _find_column_from_phrase(dataframe, target_phrase)
    if not column_name:
        return ""

    numeric_series = pd.to_numeric(
        dataframe[column_name]
        .astype(str)
        .str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce",
    ).dropna()

    if numeric_series.empty:
        return ""

    total_value = float(numeric_series.sum())
    pretty_column_name = column_name.replace("_", " ")
    return f"The sum of {pretty_column_name} is {_format_number(total_value)}."


def _find_column_from_phrase(dataframe: DataFrame, phrase: str) -> str:
    normalized_phrase = re.sub(r"[^a-z0-9]+", " ", phrase.lower()).strip()
    if not normalized_phrase:
        return ""

    phrase_variants = {normalized_phrase}
    if normalized_phrase.endswith("s"):
        phrase_variants.add(normalized_phrase[:-1])

    normalized_to_original = {
        re.sub(r"[^a-z0-9]+", " ", str(column).strip().lower()).strip(): str(column)
        for column in dataframe.columns
    }

    for variant in phrase_variants:
        for normalized_col, original_col in normalized_to_original.items():
            if variant == normalized_col:
                return original_col

    for variant in phrase_variants:
        for normalized_col, original_col in normalized_to_original.items():
            if variant in normalized_col or normalized_col in variant:
                return original_col

    return ""


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"


def _find_column(dataframe: DataFrame, aliases: list[str]) -> str:
    normalized_to_original = {
        str(column).strip().lower(): str(column)
        for column in dataframe.columns
    }

    for alias in aliases:
        if alias in normalized_to_original:
            return normalized_to_original[alias]

    for normalized_name, original_name in normalized_to_original.items():
        if any(alias in normalized_name for alias in aliases):
            return original_name

    return ""
"""Google Sheets loading helpers for dataframe chat."""
import json
import re
from pathlib import Path

import gspread
from gspread.exceptions import APIError, GSpreadException, SpreadsheetNotFound, WorksheetNotFound
import pandas as pd

from app.core.config import settings


class SheetLoadError(ValueError):
    """Raised when a Google Sheet cannot be loaded."""


_SHEET_URL_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")


def load_sheet_as_dataframe(sheet_url: str) -> pd.DataFrame:
    """Load the first worksheet from a Google Sheets URL into a dataframe."""
    spreadsheet_id = _extract_spreadsheet_id(sheet_url)
    credentials = _load_service_account_credentials()

    try:
        client = gspread.service_account_from_dict(credentials)
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.get_worksheet(0)
        if worksheet is None:
            raise SheetLoadError("Google Sheet does not contain any worksheets")
        values = worksheet.get_all_values()
    except PermissionError as exc:
        raise SheetLoadError(
            "Unable to access Google Sheet. Ensure Sheets API is enabled and the sheet is shared with the service account"
        ) from exc
    except SpreadsheetNotFound as exc:
        raise SheetLoadError("Google Sheet not found or not shared with the service account") from exc
    except WorksheetNotFound as exc:
        raise SheetLoadError("Unable to access the first worksheet in the Google Sheet") from exc
    except APIError as exc:
        raise SheetLoadError("Google Sheets API request failed. Check URL access and service account permissions") from exc
    except GSpreadException as exc:
        raise SheetLoadError(f"Failed to load Google Sheet: {exc}") from exc

    if not values:
        raise SheetLoadError("Google Sheet is empty")

    headers = [str(value).strip() for value in values[0]]
    if not any(headers):
        raise SheetLoadError("Google Sheet header row is empty")

    rows = values[1:]
    dataframe = pd.DataFrame(rows, columns=headers)
    if dataframe.empty:
        raise SheetLoadError("Google Sheet does not contain any data rows")

    return dataframe


def _extract_spreadsheet_id(sheet_url: str) -> str:
    cleaned = sheet_url.strip()
    if not cleaned:
        raise SheetLoadError("Google Sheet URL is required")

    match = _SHEET_URL_RE.search(cleaned)
    if not match:
        raise SheetLoadError("Invalid Google Sheet URL")
    return match.group(1)


def _load_service_account_credentials() -> dict[str, str]:
    credentials = _load_credentials_from_file(settings.GOOGLE_SERVICE_ACCOUNT_JSON_FILE)
    if credentials is not None:
        return credentials

    raw_json = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    credentials = _parse_credentials_json(raw_json)

    if credentials is None:
        multiline_json = _read_multiline_env_json("GOOGLE_SERVICE_ACCOUNT_JSON")
        credentials = _parse_credentials_json(multiline_json)

    if credentials is None:
        if not raw_json and not settings.GOOGLE_SERVICE_ACCOUNT_JSON_FILE:
            raise SheetLoadError(
                "Google Sheets credentials are not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON_FILE or GOOGLE_SERVICE_ACCOUNT_JSON"
            )
        raise SheetLoadError(
            "GOOGLE_SERVICE_ACCOUNT_JSON must contain the full service account JSON string or configure GOOGLE_SERVICE_ACCOUNT_JSON_FILE"
        )

    if not isinstance(credentials, dict) or not credentials.get("client_email"):
        raise SheetLoadError("Malformed Google service account credentials")
    return credentials


def _parse_credentials_json(raw_json: str | None) -> dict[str, str] | None:
    if not raw_json:
        return None

    candidate = raw_json.strip()
    if not candidate:
        return None

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        return parsed
    return None


def _load_credentials_from_file(configured_path: str | None) -> dict[str, str] | None:
    if not configured_path:
        return None

    path = Path(configured_path).expanduser()
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path

    if not path.exists():
        raise SheetLoadError(f"GOOGLE_SERVICE_ACCOUNT_JSON_FILE does not exist: {path}")

    try:
        raw_json = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SheetLoadError(f"Unable to read GOOGLE_SERVICE_ACCOUNT_JSON_FILE: {path}") from exc

    credentials = _parse_credentials_json(raw_json)
    if credentials is None:
        raise SheetLoadError(
            "GOOGLE_SERVICE_ACCOUNT_JSON_FILE must point to a valid service account JSON file"
        )

    return credentials


def _read_multiline_env_json(variable_name: str) -> str | None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return None

    env_text = env_path.read_text(encoding="utf-8")
    return _extract_multiline_json_value(env_text, variable_name)


def _extract_multiline_json_value(env_text: str, variable_name: str) -> str | None:
    marker = f"{variable_name}="
    start_index = env_text.find(marker)
    if start_index == -1:
        return None

    value_start = start_index + len(marker)
    if value_start >= len(env_text) or env_text[value_start] != "{":
        return None

    brace_depth = 0
    end_index = value_start
    for index in range(value_start, len(env_text)):
        char = env_text[index]
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth == 0:
                end_index = index + 1
                break

    if brace_depth != 0:
        return None

    return env_text[value_start:end_index].strip()
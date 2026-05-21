"""Dataframe loading and normalization services."""
import logging
from io import BytesIO
from pathlib import Path

import pandas as pd
from pandas import DataFrame
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.services.sheets_service import load_sheet_as_dataframe

logger = logging.getLogger(__name__)


class DataframeLoadError(ValueError):
    """Raised when dataframe input cannot be loaded."""


ALLOWED_DATAFRAME_EXTENSIONS = {".csv", ".xlsx"}
ALLOWED_DATAFRAME_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


async def load_uploaded_dataframe(file: UploadFile) -> DataFrame:
    """Load a CSV or XLSX upload into a normalized dataframe."""
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    mime_type = (file.content_type or "").strip().lower()

    if extension not in ALLOWED_DATAFRAME_EXTENSIONS:
        raise DataframeLoadError("Unsupported file type. Only .csv and .xlsx are allowed")
    if mime_type and mime_type not in ALLOWED_DATAFRAME_MIME_TYPES:
        raise DataframeLoadError(f"Unsupported MIME type: {mime_type}")

    content = await file.read()
    if not content:
        raise DataframeLoadError("Uploaded file is empty")
    if len(content) > settings.dataframe_max_upload_bytes:
        raise DataframeLoadError(
            f"File exceeds max size ({settings.DATAFRAME_MAX_UPLOAD_MB} MB)"
        )

    try:
        if extension == ".csv":
            logger.info(f"Parsing CSV file: {filename}, size: {len(content)} bytes")
            # Try multiple encodings for CSV files
            dataframe = _read_csv_with_encoding_fallback(content)
            logger.info(f"CSV parsed successfully: {dataframe.shape}")
        else:
            logger.info(f"Parsing Excel file: {filename}, size: {len(content)} bytes")
            dataframe = pd.read_excel(BytesIO(content), engine="openpyxl")
            logger.info(f"Excel parsed successfully: {dataframe.shape}")
    except Exception as exc:
        logger.exception(f"Failed to parse {extension} file: {exc}")
        raise DataframeLoadError(f"Failed to parse {extension} file") from exc

    return normalize_dataframe(dataframe)


def load_google_sheet_dataframe(sheet_url: str) -> DataFrame:
    """Load a Google Sheet URL into a normalized dataframe."""
    dataframe = load_sheet_as_dataframe(sheet_url)
    return normalize_dataframe(dataframe)


def normalize_dataframe(dataframe: DataFrame) -> DataFrame:
    """Normalize columns and remove fully empty rows and columns."""
    normalized = dataframe.copy()
    normalized = normalized.dropna(axis=0, how="all").dropna(axis=1, how="all")
    normalized.columns = _normalize_columns(normalized.columns)
    if normalized.empty or normalized.shape[1] == 0:
        raise DataframeLoadError("Dataframe is empty after normalization")
    return normalized.reset_index(drop=True)


def summarize_dataframe(dataframe: DataFrame) -> dict[str, object]:
    """Return a small serializable summary for UI responses."""
    preview = dataframe.head(5).where(pd.notna(dataframe.head(5)), None)
    return {
        "row_count": int(len(dataframe.index)),
        "column_count": int(len(dataframe.columns)),
        "columns": [str(column) for column in dataframe.columns],
        "preview_rows": preview.to_dict(orient="records"),
    }


def _read_csv_with_encoding_fallback(content: bytes) -> DataFrame:
    """Try to read CSV with multiple encodings, falling back if UTF-8 fails."""
    encodings = ["utf-8-sig", "utf-8", "latin-1", "iso-8859-1", "cp1252", "windows-1252"]
    last_error = None

    for encoding in encodings:
        try:
            logger.debug(f"Attempting to parse CSV with encoding: {encoding}")
            return pd.read_csv(BytesIO(content), on_bad_lines="skip", encoding=encoding)
        except (UnicodeDecodeError, LookupError) as e:
            last_error = e
            logger.debug(f"Encoding {encoding} failed: {e}")
            continue

    # If all encodings fail, raise the last error
    raise last_error or DataframeLoadError("Could not parse CSV file with any supported encoding")


def _normalize_columns(columns: pd.Index) -> list[str]:
    seen: dict[str, int] = {}
    normalized_columns: list[str] = []

    for index, column in enumerate(columns, start=1):
        base = str(column).strip() or f"column_{index}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        normalized_columns.append(base if count == 0 else f"{base}_{count + 1}")

    return normalized_columns
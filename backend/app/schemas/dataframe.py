"""Schemas for dataframe chat endpoints."""
from typing import Any

from pydantic import BaseModel, Field


class DataframeSourceResponse(BaseModel):
    source_type: str
    source_name: str
    row_count: int
    column_count: int
    columns: list[str]
    preview_rows: list[dict[str, Any]]


class GoogleSheetConnectRequest(BaseModel):
    sheet_url: str = Field(..., min_length=1, max_length=4000)


class DataframeQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)


class DataframeQueryResponse(BaseModel):
    answer: str
    source_type: str
    source_name: str
    row_count: int
    column_count: int
    columns: list[str]
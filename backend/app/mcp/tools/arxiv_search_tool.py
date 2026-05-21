"""MCP tool for searching arXiv papers."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ai.tools.arxiv_tool import ArxivToolError, search_arxiv_papers


class ArxivPaperOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    arxiv_url: str


class ArxivSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=240)
    max_results: int = Field(default=10, ge=1, le=25)
    timeout_seconds: float = Field(default=20.0, ge=1.0, le=120.0)


class ArxivSearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    count: int
    papers: list[ArxivPaperOutput]


class ArxivSearchTool:
    """Tool adapter exposing arXiv search in MCP format."""

    name = "arxiv.search"
    description = "Search arXiv for papers by topic and return normalized metadata."
    input_model = ArxivSearchInput
    output_model = ArxivSearchOutput

    async def execute(self, payload: ArxivSearchInput) -> dict[str, Any]:
        try:
            papers = await search_arxiv_papers(
                query=payload.query,
                max_results=payload.max_results,
                timeout_seconds=payload.timeout_seconds,
            )
        except ArxivToolError as exc:
            raise RuntimeError(str(exc)) from exc

        return {
            "query": payload.query,
            "count": len(papers),
            "papers": [paper.to_dict() for paper in papers],
        }

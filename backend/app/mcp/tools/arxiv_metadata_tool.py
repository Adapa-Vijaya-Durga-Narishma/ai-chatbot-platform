"""MCP tool for retrieving metadata for a specific arXiv paper."""
from __future__ import annotations

import re
from typing import Any
import xml.etree.ElementTree as ET

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_ARXIV_ID_FROM_URL = re.compile(r"/(?:abs|pdf)/([^/?#]+)")


class ArxivPaperOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    arxiv_url: str


class ArxivMetadataInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arxiv_id: str | None = Field(default=None, max_length=80)
    arxiv_url: str | None = Field(default=None, max_length=500)
    timeout_seconds: float = Field(default=20.0, ge=1.0, le=120.0)

    @model_validator(mode="after")
    def validate_identifier(self) -> "ArxivMetadataInput":
        if not (self.arxiv_id or self.arxiv_url):
            raise ValueError("Either arxiv_id or arxiv_url must be provided.")
        return self


class ArxivMetadataOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper: ArxivPaperOutput


class ArxivMetadataTool:
    """Tool adapter exposing paper metadata lookup in MCP format."""

    name = "arxiv.metadata"
    description = "Retrieve metadata for a specific arXiv paper by ID or URL."
    input_model = ArxivMetadataInput
    output_model = ArxivMetadataOutput

    async def execute(self, payload: ArxivMetadataInput) -> dict[str, Any]:
        arxiv_id = payload.arxiv_id or _extract_id_from_url(payload.arxiv_url or "")
        if not arxiv_id:
            raise RuntimeError("Could not determine arXiv identifier from input.")

        params = {
            "id_list": arxiv_id,
            "start": 0,
            "max_results": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(payload.timeout_seconds)) as client:
                response = await client.get(ARXIV_API_URL, params=params)
        except httpx.TimeoutException as exc:
            raise RuntimeError("arXiv metadata request timed out") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("Failed to connect to arXiv") from exc

        if response.status_code != 200:
            raise RuntimeError(f"arXiv returned status code {response.status_code}")

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise RuntimeError("Could not parse arXiv response") from exc

        entry = root.find("atom:entry", ATOM_NS)
        if entry is None:
            raise RuntimeError("No paper found for the provided identifier")

        paper = _entry_to_paper(entry)
        return {"paper": paper}


def _extract_id_from_url(value: str) -> str:
    match = _ARXIV_ID_FROM_URL.search(value.strip())
    if not match:
        return ""
    return match.group(1).replace(".pdf", "")


def _entry_to_paper(entry: ET.Element) -> dict[str, Any]:
    identifier = _text(entry, "atom:id")
    title = _collapse_whitespace(_text(entry, "atom:title"))
    abstract = _collapse_whitespace(_text(entry, "atom:summary"))
    published = _text(entry, "atom:published")
    authors = [_collapse_whitespace(author.text or "") for author in entry.findall("atom:author/atom:name", ATOM_NS)]
    authors = [author for author in authors if author]

    arxiv_url = ""
    for link in entry.findall("atom:link", ATOM_NS):
        if (link.attrib.get("rel") or "").lower() == "alternate":
            arxiv_url = link.attrib.get("href", "")
            break
    if not arxiv_url:
        arxiv_url = identifier

    return {
        "arxiv_id": identifier.rsplit("/", 1)[-1] if identifier else "",
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published": published,
        "arxiv_url": arxiv_url,
    }


def _text(entry: ET.Element, xpath: str) -> str:
    node = entry.find(xpath, ATOM_NS)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())

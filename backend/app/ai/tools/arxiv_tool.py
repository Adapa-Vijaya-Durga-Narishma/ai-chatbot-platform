"""arXiv API integration utilities for research digest workflows."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import xml.etree.ElementTree as ET

import httpx

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3.0


class ArxivToolError(RuntimeError):
    """Raised when arXiv search fails or returns invalid data."""


@dataclass(slots=True)
class ArxivPaper:
    """Normalized paper metadata from arXiv."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    arxiv_url: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


async def search_arxiv_papers(
    query: str,
    max_results: int = 10,
    timeout_seconds: float = 20.0,
) -> list[ArxivPaper]:
    """Search arXiv with relevance sorting and return normalized papers."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    safe_max_results = max(1, min(max_results, 25))
    params = {
        "search_query": f"all:{cleaned_query}",
        "start": 0,
        "max_results": safe_max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:
            last_error: Exception | None = None
            response = None
            for attempt in range(MAX_RETRIES):
                try:
                    response = await client.get(ARXIV_API_URL, params=params)
                    # Retry on rate limit or server errors
                    if response.status_code in (429, 500, 502, 503, 504):
                        delay = RETRY_DELAY_SECONDS * (attempt + 1)
                        await asyncio.sleep(delay)
                        continue
                    break
                except httpx.HTTPError as exc:
                    last_error = exc
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
            else:
                if last_error:
                    raise ArxivToolError("Failed to connect to arXiv after retries") from last_error
                status = response.status_code if response else "unknown"
                raise ArxivToolError(f"arXiv unavailable (status {status}) - please try again later")
    except httpx.TimeoutException as exc:
        raise ArxivToolError("arXiv request timed out") from exc
    except httpx.HTTPError as exc:
        raise ArxivToolError("Failed to connect to arXiv") from exc

    if response.status_code == 429:
        raise ArxivToolError("arXiv rate limit exceeded - please wait a moment and retry")

    if response.status_code != 200:
        raise ArxivToolError(f"arXiv returned status code {response.status_code}")

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        raise ArxivToolError("Could not parse arXiv response") from exc

    papers: list[ArxivPaper] = []
    for entry in root.findall("atom:entry", ATOM_NS):
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

        if not title or not abstract:
            continue

        papers.append(
            ArxivPaper(
                arxiv_id=identifier.rsplit("/", 1)[-1] if identifier else "",
                title=title,
                authors=authors,
                abstract=abstract,
                published=published,
                arxiv_url=arxiv_url,
            )
        )

    return papers


def _text(entry: ET.Element, xpath: str) -> str:
    node = entry.find(xpath, ATOM_NS)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())

"""Autonomous research digest agent orchestrated via LangGraph."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.ai.llm import llm
from app.ai.agents.research_graph import (
    ArxivPaper,
    EvidenceDecision,
    ResearchState,
    _build_research_graph,
)
from app.core.config import settings
from app.mcp.client import MCPClient


class ResearchDigestAgent:
    """Runs an iterative research loop orchestrated via LangGraph."""

    def __init__(self) -> None:
        prompts_dir = Path(__file__).parent.parent / "prompts"

        planner_prompt_text = (prompts_dir / "research_planner_prompt.txt").read_text(encoding="utf-8")
        evidence_prompt_text = (prompts_dir / "evidence_evaluation_prompt.txt").read_text(encoding="utf-8")
        digest_prompt_text = (prompts_dir / "research_digest_prompt.txt").read_text(encoding="utf-8")

        self._planner_chain = (
            PromptTemplate(
                template=planner_prompt_text,
                input_variables=["topic", "iteration", "max_iterations", "prior_queries", "known_papers"],
            )
            | llm
            | StrOutputParser()
        )

        self._evidence_chain = (
            PromptTemplate(
                template=evidence_prompt_text,
                input_variables=[
                    "topic",
                    "iteration",
                    "max_iterations",
                    "unique_papers_count",
                    "recent_titles",
                    "reasoning_log",
                ],
            )
            | llm
            | StrOutputParser()
        )

        self._digest_chain = (
            PromptTemplate(
                template=digest_prompt_text,
                input_variables=["topic", "papers_json", "reasoning_log", "iterations_used"],
            )
            | llm
            | StrOutputParser()
        )

        self.max_iterations = max(1, min(settings.RESEARCH_AGENT_MAX_ITERATIONS, 8))
        self._mcp_client = MCPClient(default_timeout_seconds=settings.RESEARCH_AGENT_TIMEOUT_SECONDS)

        self._graph = _build_research_graph(
            mcp_client=self._mcp_client,
            planner_chain=self._planner_chain,
            evidence_chain=self._evidence_chain,
            digest_chain=self._digest_chain,
            event_callback=self._emit_event,
        )
        self._events: list[dict[str, Any]] = []

    def _emit_event(self, event: dict[str, Any]) -> None:
        """Collect event for streaming."""
        self._events.append(event)

    async def stream_research(self, topic: str, user_email: str):
        """Yield structured research events as the LangGraph workflow progresses."""
        self._events.clear()

        initial_state: ResearchState = {
            "topic": topic,
            "user_email": user_email,
            "iteration": 1,
            "max_iterations": self.max_iterations,
            "seen_papers": {},
            "prior_queries": [],
            "reasoning_log": [],
            "no_new_paper_rounds": 0,
            "current_query": topic,
            "discovered_papers": [],
            "evidence_decision": None,
            "should_stop": False,
            "iterations_used": 0,
            "final_digest": "",
        }

        try:
            final_state = await self._graph.ainvoke(initial_state)
        except Exception as exc:
            yield {
                "type": "error",
                "error": "research_failure",
                "message": str(exc),
            }
            return

        for event in self._events:
            yield event

        papers = list(final_state.get("seen_papers", {}).values())
        digest = final_state.get("final_digest", "")

        for section in self._split_digest_sections(digest):
            yield {
                "type": "digest_section",
                "section": section,
            }

        yield {
            "type": "done",
            "digest": digest,
            "iterations_used": final_state.get("iterations_used", 0),
            "paper_count": len(papers),
        }

    def _split_digest_sections(self, digest: str) -> list[dict[str, str]]:
        import re

        required_sections = [
            "Topic Overview",
            "Key Findings",
            "Important Papers",
            "Emerging Trends",
            "Limitations / Open Problems",
            "References",
        ]

        pattern = re.compile(
            r"^##\s+(Topic Overview|Key Findings|Important Papers|Emerging Trends|Limitations / Open Problems|References)\s*$",
            flags=re.MULTILINE,
        )
        matches = list(pattern.finditer(digest))

        if not matches:
            return [{"title": "Research Digest", "content": digest.strip()}]

        sections: list[dict[str, str]] = []
        for index, match in enumerate(matches):
            title = match.group(1)
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(digest)
            content = digest[start:end].strip()
            sections.append({"title": title, "content": content})

        seen_titles = {section["title"] for section in sections}
        for title in required_sections:
            if title not in seen_titles:
                sections.append({"title": title, "content": "Not enough evidence collected for this section."})

        return sections

    def _build_empty_digest(self, topic: str) -> str:
        return (
            f"## Topic Overview\n"
            f"No arXiv papers were retrieved for topic: {topic}.\n\n"
            "## Key Findings\n"
            "No findings could be extracted because the search returned no results.\n\n"
            "## Important Papers\n"
            "No papers identified.\n\n"
            "## Emerging Trends\n"
            "Insufficient evidence.\n\n"
            "## Limitations / Open Problems\n"
            "The current query may be too narrow; broaden search terms and retry.\n\n"
            "## References\n"
            "No references available."
        )

"""LangGraph-based research digest workflow orchestration."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import json
from typing import Any, TypedDict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END

from app.ai.llm import llm
from app.core.config import settings
from app.mcp.client import MCPClient, MCPClientError, MCPToolNotFoundError


class ArxivToolError(RuntimeError):
    """Raised when arXiv MCP tool execution fails."""


@dataclass(slots=True)
class ArxivPaper:
    """Normalized paper metadata for research digest workflows."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    arxiv_url: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class EvidenceDecision:
    is_sufficient: bool
    coverage_score: float
    repeated_findings: bool
    reasoning: str
    next_focus: str


class ResearchState(TypedDict):
    """State container for research digest workflow."""

    topic: str
    user_email: str
    iteration: int
    max_iterations: int
    seen_papers: dict[str, ArxivPaper]
    prior_queries: list[str]
    reasoning_log: list[str]
    no_new_paper_rounds: int
    current_query: str
    discovered_papers: list[ArxivPaper]
    evidence_decision: EvidenceDecision | None
    should_stop: bool
    iterations_used: int
    final_digest: str


def _build_research_graph(
    mcp_client: MCPClient,
    planner_chain: Any,
    evidence_chain: Any,
    digest_chain: Any,
    event_callback: Any,
) -> Any:
    """Build LangGraph workflow for research digest orchestration."""
    graph = StateGraph(ResearchState)

    async def plan_node(state: ResearchState) -> dict[str, Any]:
        """Plan next search query."""
        event_callback({
            "type": "status",
            "stage": "searching",
            "message": f"Searching arXiv (iteration {state['iteration']}/{state['max_iterations']})...",
            "iteration": state["iteration"],
            "query": state["topic"],
        })

        known_titles = [paper.title for paper in state["seen_papers"].values()]
        response_text = await planner_chain.ainvoke(
            {
                "topic": state["topic"],
                "iteration": state["iteration"],
                "max_iterations": state["max_iterations"],
                "prior_queries": json.dumps(state["prior_queries"][-6:], ensure_ascii=True),
                "known_papers": json.dumps(known_titles[-8:], ensure_ascii=True),
            },
            config={"metadata": {"user_email": state["user_email"]}},
        )

        payload = _extract_json_object(response_text)
        query = str(payload.get("search_query", "") if payload else "").strip()
        if not query:
            query = state["topic"]

        return {
            "current_query": query,
            "prior_queries": state["prior_queries"] + [query],
        }

    async def search_node(state: ResearchState) -> dict[str, Any]:
        """Search arXiv for papers via MCP."""
        try:
            discovered = await _search_arxiv_papers_via_mcp(
                mcp_client=mcp_client,
                query=state["current_query"],
                max_results=max(2, min(settings.ARXIV_MAX_RESULTS, 15)),
                timeout_seconds=settings.RESEARCH_AGENT_TIMEOUT_SECONDS,
            )
        except ArxivToolError as exc:
            if not state["seen_papers"]:
                event_callback({
                    "type": "error",
                    "error": "arxiv_failure",
                    "message": str(exc),
                    "iteration": state["iteration"],
                })
                return {"should_stop": True, "discovered_papers": []}
            return {"discovered_papers": [], "should_stop": False}

        new_papers: list[ArxivPaper] = []
        max_total_papers = min(40, state["max_iterations"] * max(2, min(settings.ARXIV_MAX_RESULTS, 15)))
        seen = state["seen_papers"].copy()

        for paper in discovered:
            if len(seen) >= max_total_papers:
                break
            key = paper.arxiv_url or paper.arxiv_id or paper.title
            if key in seen:
                continue
            seen[key] = paper
            new_papers.append(paper)
            event_callback({
                "type": "paper",
                "paper": paper.to_dict(),
                "iteration": state["iteration"],
            })

        return {
            "seen_papers": seen,
            "discovered_papers": new_papers,
            "no_new_paper_rounds": 0 if new_papers else state["no_new_paper_rounds"] + 1,
        }

    async def evaluate_node(state: ResearchState) -> dict[str, Any]:
        """Evaluate evidence sufficiency."""
        event_callback({
            "type": "status",
            "stage": "evaluating",
            "message": "Evaluating evidence sufficiency...",
            "iteration": state["iteration"],
            "unique_papers": len(state["seen_papers"]),
        })

        response_text = await evidence_chain.ainvoke(
            {
                "topic": state["topic"],
                "iteration": state["iteration"],
                "max_iterations": state["max_iterations"],
                "unique_papers_count": len(state["seen_papers"]),
                "recent_titles": json.dumps([p.title for p in state["discovered_papers"][:8]], ensure_ascii=True),
                "reasoning_log": json.dumps(state["reasoning_log"][-6:], ensure_ascii=True),
            },
            config={"metadata": {"user_email": state["user_email"]}},
        )

        payload = _extract_json_object(response_text)
        if payload:
            decision = EvidenceDecision(
                is_sufficient=bool(payload.get("is_sufficient", False)),
                coverage_score=float(max(0.0, min(1.0, payload.get("coverage_score", 0.0) or 0.0))),
                repeated_findings=bool(payload.get("repeated_findings", False)),
                reasoning=str(payload.get("reasoning", "Evidence evaluated.")).strip() or "Evidence evaluated.",
                next_focus=str(payload.get("next_focus", "")).strip(),
            )
        else:
            decision = EvidenceDecision(
                is_sufficient=False,
                coverage_score=0.5,
                repeated_findings=False,
                reasoning="Unable to parse evaluator output; continuing with conservative defaults.",
                next_focus="Seek additional papers with broader multimodal evaluation evidence.",
            )

        return {
            "evidence_decision": decision,
            "reasoning_log": state["reasoning_log"] + [decision.reasoning],
        }

    async def decide_node(state: ResearchState) -> dict[str, Any]:
        """Decide whether to continue or stop iteration loop."""
        target_papers = min(max(6, max(2, min(settings.ARXIV_MAX_RESULTS, 15)) // 2 + 3), 12)
        max_total_papers = min(40, state["max_iterations"] * max(2, min(settings.ARXIV_MAX_RESULTS, 15)))
        decision = state["evidence_decision"]

        count_sufficient = len(state["seen_papers"]) >= target_papers
        coverage_sufficient = decision.coverage_score >= 0.7
        repeated_signal = decision.repeated_findings or state["no_new_paper_rounds"] >= 2
        llm_sufficient = decision.is_sufficient

        stop_reasons: list[str] = []
        if count_sufficient:
            stop_reasons.append("enough_unique_papers")
        if coverage_sufficient:
            stop_reasons.append("topic_coverage_sufficient")
        if repeated_signal:
            stop_reasons.append("repeated_findings")
        if state["iteration"] >= state["max_iterations"]:
            stop_reasons.append("max_iterations_reached")

        should_stop = (
            (count_sufficient and coverage_sufficient)
            or (llm_sufficient and count_sufficient)
            or repeated_signal
            or state["iteration"] >= state["max_iterations"]
            or len(state["seen_papers"]) >= max_total_papers
        )

        event_callback({
            "type": "reasoning",
            "iteration": state["iteration"],
            "message": decision.reasoning,
            "coverage_score": decision.coverage_score,
            "is_sufficient": should_stop,
            "next_focus": decision.next_focus,
            "stop_reasons": stop_reasons,
        })

        return {"should_stop": should_stop, "iterations_used": state["iteration"]}

    async def generate_digest_node(state: ResearchState) -> dict[str, Any]:
        """Generate final research digest."""
        event_callback({
            "type": "status",
            "stage": "generating",
            "message": "Generating structured research digest...",
            "iteration": state["iterations_used"],
        })

        if not state["seen_papers"]:
            digest = _build_empty_digest(state["topic"])
        else:
            paper_payload = [paper.to_dict() for paper in list(state["seen_papers"].values())[:20]]
            digest_text = await digest_chain.ainvoke(
                {
                    "topic": state["topic"],
                    "papers_json": json.dumps(paper_payload, ensure_ascii=True),
                    "reasoning_log": json.dumps(state["reasoning_log"][-10:], ensure_ascii=True),
                    "iterations_used": state["iterations_used"],
                },
                config={"metadata": {"user_email": state["user_email"]}},
            )
            digest = digest_text.strip() if digest_text.strip() else _build_empty_digest(state["topic"])

        return {"final_digest": digest}

    async def delay_node(state: ResearchState) -> dict[str, Any]:
        """Add delay between iterations to avoid rate limiting."""
        await asyncio.sleep(2.0)
        return {"iteration": state["iteration"] + 1}

    def continue_loop(state: ResearchState) -> str:
        """Determine whether to continue loop or finish."""
        if state["should_stop"]:
            return "finish"
        if state["iteration"] >= state["max_iterations"]:
            return "finish"
        return "delay"

    graph.add_node("plan", plan_node)
    graph.add_node("search", search_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("decide", decide_node)
    graph.add_node("delay", delay_node)
    graph.add_node("generate_digest", generate_digest_node)

    graph.add_edge("plan", "search")
    graph.add_edge("search", "evaluate")
    graph.add_edge("evaluate", "decide")
    graph.add_conditional_edges(
        "decide",
        continue_loop,
        {
            "delay": "delay",
            "finish": "generate_digest",
        },
    )
    graph.add_edge("delay", "plan")
    graph.add_edge("generate_digest", END)

    graph.set_entry_point("plan")

    return graph.compile()


async def _search_arxiv_papers_via_mcp(
    mcp_client: MCPClient,
    query: str,
    max_results: int,
    timeout_seconds: float,
) -> list[ArxivPaper]:
    """Execute arXiv search via MCP client."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    try:
        result = await mcp_client.invoke_tool(
            "arxiv.search",
            {
                "query": cleaned_query,
                "max_results": max_results,
                "timeout_seconds": timeout_seconds,
            },
            timeout_seconds=timeout_seconds,
        )
    except MCPToolNotFoundError as exc:
        raise ArxivToolError("Required MCP tool not available: arxiv.search") from exc
    except MCPClientError as exc:
        raise ArxivToolError(str(exc)) from exc

    papers_payload = result.get("papers")
    if not isinstance(papers_payload, list):
        raise ArxivToolError("Invalid MCP response: papers list missing")

    papers: list[ArxivPaper] = []
    for item in papers_payload:
        if not isinstance(item, dict):
            continue
        papers.append(
            ArxivPaper(
                arxiv_id=str(item.get("arxiv_id", "")),
                title=str(item.get("title", "")),
                authors=[str(author) for author in item.get("authors", []) if str(author).strip()],
                abstract=str(item.get("abstract", "")),
                published=str(item.get("published", "")),
                arxiv_url=str(item.get("arxiv_url", "")),
            )
        )
    return papers


def _extract_json_object(value: str) -> dict[str, Any] | None:
    """Extract JSON object from string."""
    import re
    match = re.search(r"\{[\s\S]*\}", value)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def _build_empty_digest(topic: str) -> str:
    """Build fallback digest when no papers found."""
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

import pytest

from app.ai.agents.research_agent import ResearchDigestAgent


class StubChain:
    def __init__(self, response: str) -> None:
        self._response = response

    async def ainvoke(self, *_args, **_kwargs) -> str:
        return self._response


class StubMCPClient:
    async def discover_tools(self) -> list[dict[str, object]]:
        return [{"name": "arxiv.search"}]

    async def invoke_tool(self, _tool_name: str, _arguments: dict[str, object], **_kwargs) -> dict[str, object]:
        return {
            "query": "test query",
            "count": 1,
            "papers": [
                {
                    "arxiv_id": "2401.00001",
                    "title": "A Test Paper",
                    "authors": ["Jane Doe"],
                    "abstract": "This is a test abstract.",
                    "published": "2024-01-01T00:00:00Z",
                    "arxiv_url": "https://arxiv.org/abs/2401.00001",
                }
            ],
        }


@pytest.mark.asyncio
async def test_research_agent_stream_uses_langgraph() -> None:
    agent = ResearchDigestAgent()

    agent._planner_chain = StubChain('{"search_query":"multimodal evaluation"}')
    agent._evidence_chain = StubChain(
        '{"is_sufficient":true,"coverage_score":0.9,"repeated_findings":false,'
        '"reasoning":"Sufficient evidence collected.","next_focus":""}'
    )
    agent._digest_chain = StubChain(
        "## Topic Overview\nOverview\n\n"
        "## Key Findings\nFindings\n\n"
        "## Important Papers\nPaper list\n\n"
        "## Emerging Trends\nTrends\n\n"
        "## Limitations / Open Problems\nLimitations\n\n"
        "## References\n- https://arxiv.org/abs/2401.00001"
    )
    agent._mcp_client = StubMCPClient()

    # Rebuild graph with stub chains
    from app.ai.agents.research_graph import _build_research_graph
    agent._graph = _build_research_graph(
        mcp_client=agent._mcp_client,
        planner_chain=agent._planner_chain,
        evidence_chain=agent._evidence_chain,
        digest_chain=agent._digest_chain,
        event_callback=agent._emit_event,
    )

    events = [event async for event in agent.stream_research("Multimodal LLM benchmark", "user@example.com")]

    assert any(event.get("type") == "paper" for event in events)
    done_event = next(event for event in events if event.get("type") == "done")
    assert done_event["paper_count"] == 1
    assert "Topic Overview" in done_event["digest"]

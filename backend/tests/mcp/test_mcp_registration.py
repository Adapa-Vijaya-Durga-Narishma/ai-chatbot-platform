from app.mcp.server import MCPServer
from app.mcp.tools.arxiv_metadata_tool import ArxivMetadataTool
from app.mcp.tools.arxiv_search_tool import ArxivSearchTool


def test_mcp_tool_registration_and_metadata() -> None:
    server = MCPServer(enabled=True, host="127.0.0.1", port=8811)
    server.register_tool(ArxivSearchTool())
    server.register_tool(ArxivMetadataTool())

    tools = server.list_tools()
    names = {tool["name"] for tool in tools}

    assert "arxiv.search" in names
    assert "arxiv.metadata" in names

    for tool in tools:
        assert "description" in tool
        assert "input_schema" in tool
        assert "output_schema" in tool
        assert tool["input_schema"].get("type") == "object"
        assert tool["output_schema"].get("type") == "object"

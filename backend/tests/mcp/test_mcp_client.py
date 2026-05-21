import pytest

from app.mcp.client import MCPClient, MCPClientError, MCPToolNotFoundError
from app.mcp.server import MCPServer
from app.mcp.tools.arxiv_search_tool import ArxivSearchTool


@pytest.mark.asyncio
async def test_mcp_client_discovery() -> None:
    server = MCPServer(enabled=True, host="127.0.0.1", port=8811)
    server.register_tool(ArxivSearchTool())

    client = MCPClient(server=server)
    tools = await client.discover_tools()

    assert any(tool["name"] == "arxiv.search" for tool in tools)


@pytest.mark.asyncio
async def test_mcp_client_missing_tool_error() -> None:
    server = MCPServer(enabled=True, host="127.0.0.1", port=8811)
    client = MCPClient(server=server)

    with pytest.raises(MCPToolNotFoundError):
        await client.invoke_tool("missing.tool", {"x": 1})


@pytest.mark.asyncio
async def test_mcp_client_disabled_server() -> None:
    server = MCPServer(enabled=False, host="127.0.0.1", port=8811)
    client = MCPClient(server=server)

    with pytest.raises(MCPClientError):
        await client.discover_tools()

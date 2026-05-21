"""MCP client abstraction used by AI agents."""
from __future__ import annotations

from typing import Any

from app.mcp.server import MCPServer, get_mcp_server


class MCPClientError(RuntimeError):
    """Base MCP client exception."""


class MCPToolNotFoundError(MCPClientError):
    """Raised when a requested tool does not exist."""


class MCPClient:
    """Client for MCP discovery + tool invocation."""

    def __init__(
        self,
        *,
        server: MCPServer | None = None,
        default_timeout_seconds: float = 20.0,
    ) -> None:
        self._server = server
        self._default_timeout_seconds = default_timeout_seconds

    @property
    def _connected_server(self) -> MCPServer:
        server = self._server or get_mcp_server()
        if not server.enabled:
            raise MCPClientError("MCP server is disabled.")
        return server

    async def discover_tools(self) -> list[dict[str, Any]]:
        return self._connected_server.list_tools()

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        server = self._connected_server
        response = await server.execute_tool(
            tool_name,
            arguments,
            timeout_seconds=self._default_timeout_seconds if timeout_seconds is None else timeout_seconds,
        )

        if response.get("ok"):
            return response["result"]

        error = response.get("error") or {}
        code = str(error.get("code", "mcp_error"))
        message = str(error.get("message", "MCP tool invocation failed."))

        if code == "tool_not_found":
            raise MCPToolNotFoundError(message)

        raise MCPClientError(f"{code}: {message}")

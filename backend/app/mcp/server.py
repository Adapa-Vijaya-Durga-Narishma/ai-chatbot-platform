"""In-process MCP server for tool registration and execution."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from app.core.config import settings


class MCPServerError(RuntimeError):
    """Raised when the MCP server cannot process a request."""


class MCPTool(Protocol):
    """Contract for MCP-compatible tools."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    async def execute(self, payload: BaseModel) -> BaseModel | dict[str, Any]:
        """Execute tool logic for validated input payload."""


@dataclass(slots=True)
class _RegisteredTool:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    implementation: MCPTool


class MCPServer:
    """Minimal MCP server abstraction exposing discover + execute primitives."""

    def __init__(self, *, enabled: bool, host: str, port: int) -> None:
        self.enabled = enabled
        self.host = host
        self.port = port
        self._tools: dict[str, _RegisteredTool] = {}

    def register_tool(self, tool: MCPTool) -> None:
        if tool.name in self._tools:
            raise MCPServerError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = _RegisteredTool(
            name=tool.name,
            description=tool.description,
            input_model=tool.input_model,
            output_model=tool.output_model,
            implementation=tool,
        )

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_model.model_json_schema(),
                "output_schema": tool.output_model.model_json_schema(),
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        timeout_seconds: float = 20.0,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {
                "ok": False,
                "error": {
                    "code": "mcp_disabled",
                    "message": "MCP server is disabled.",
                },
            }

        tool = self._tools.get(tool_name)
        if tool is None:
            return {
                "ok": False,
                "error": {
                    "code": "tool_not_found",
                    "message": f"Tool not found: {tool_name}",
                },
            }

        try:
            payload = tool.input_model.model_validate(arguments)
        except ValidationError as exc:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_input",
                    "message": "Tool input validation failed.",
                    "details": exc.errors(include_url=False),
                },
            }

        try:
            result = await asyncio.wait_for(tool.implementation.execute(payload), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            return {
                "ok": False,
                "error": {
                    "code": "tool_timeout",
                    "message": f"Tool execution timed out after {timeout_seconds} seconds.",
                },
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "ok": False,
                "error": {
                    "code": "tool_execution_failed",
                    "message": str(exc),
                },
            }

        try:
            validated_output = tool.output_model.model_validate(result)
        except ValidationError as exc:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_output",
                    "message": "Tool output validation failed.",
                    "details": exc.errors(include_url=False),
                },
            }

        return {
            "ok": True,
            "tool": tool_name,
            "result": validated_output.model_dump(mode="json"),
        }


def _register_default_tools(server: MCPServer) -> None:
    from app.mcp.tools.arxiv_metadata_tool import ArxivMetadataTool
    from app.mcp.tools.arxiv_search_tool import ArxivSearchTool

    server.register_tool(ArxivSearchTool())
    server.register_tool(ArxivMetadataTool())


_server_instance: MCPServer | None = None


def get_mcp_server() -> MCPServer:
    """Return a singleton MCP server with dynamic tool registration."""
    global _server_instance

    if _server_instance is None:
        _server_instance = MCPServer(
            enabled=settings.MCP_SERVER_ENABLED,
            host=settings.MCP_SERVER_HOST,
            port=settings.MCP_SERVER_PORT,
        )
        _register_default_tools(_server_instance)
    return _server_instance

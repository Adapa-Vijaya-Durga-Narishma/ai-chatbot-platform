import asyncio

import pytest
from pydantic import BaseModel, ConfigDict, Field

from app.mcp.server import MCPServer


class EchoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)


class EchoOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    echoed: str


class EchoTool:
    name = "test.echo"
    description = "Echo test tool"
    input_model = EchoInput
    output_model = EchoOutput

    async def execute(self, payload: EchoInput) -> dict[str, str]:
        return {"echoed": payload.message}


class SlowTool:
    name = "test.slow"
    description = "Slow test tool"
    input_model = EchoInput
    output_model = EchoOutput

    async def execute(self, payload: EchoInput) -> dict[str, str]:
        await asyncio.sleep(0.2)
        return {"echoed": payload.message}


@pytest.mark.asyncio
async def test_mcp_execute_success() -> None:
    server = MCPServer(enabled=True, host="127.0.0.1", port=8811)
    server.register_tool(EchoTool())

    response = await server.execute_tool("test.echo", {"message": "hello"})

    assert response["ok"] is True
    assert response["result"]["echoed"] == "hello"


@pytest.mark.asyncio
async def test_mcp_execute_invalid_input_schema() -> None:
    server = MCPServer(enabled=True, host="127.0.0.1", port=8811)
    server.register_tool(EchoTool())

    response = await server.execute_tool("test.echo", {"bad": "payload"})

    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_input"


@pytest.mark.asyncio
async def test_mcp_execute_timeout() -> None:
    server = MCPServer(enabled=True, host="127.0.0.1", port=8811)
    server.register_tool(SlowTool())

    response = await server.execute_tool("test.slow", {"message": "hello"}, timeout_seconds=0.01)

    assert response["ok"] is False
    assert response["error"]["code"] == "tool_timeout"

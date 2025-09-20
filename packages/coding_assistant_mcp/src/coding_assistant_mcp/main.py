from __future__ import annotations
import asyncio

from fastmcp import FastMCP

from coding_assistant_mcp.todo import todo_server


async def main() -> None:
    # Create FastMCP server instance first so we can decorate tools.
    mcp = FastMCP("Coding Assistant MCP")
    await mcp.import_server(todo_server, prefix="todo")
    await mcp.run_async()


asyncio.run(main())

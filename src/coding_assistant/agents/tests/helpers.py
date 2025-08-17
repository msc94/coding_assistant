from dataclasses import dataclass
from typing import Iterable, Sequence
from unittest.mock import AsyncMock, Mock

from coding_assistant.agents.parameters import Parameter
from coding_assistant.agents.types import Agent, Tool
from coding_assistant.tools.mcp import MCPServer
from coding_assistant.ui import UI


@dataclass
class FakeFunction:
    name: str
    arguments: str = "{}"


@dataclass
class FakeToolCall:
    id: str
    function: FakeFunction


async def no_feedback(_: Agent):
    """A feedback function that returns no feedback (used in tests)."""
    return None


def make_ui_mock(*, ask_value: str | None = None, confirm_value: bool = True) -> UI:
    ui = Mock()

    async def _ask(prompt_text: str, default: str | None = None) -> str:
        return ask_value if ask_value is not None else (default or "")

    async def _confirm(prompt_text: str) -> bool:
        return bool(confirm_value)

    ui.ask = AsyncMock(side_effect=_ask)
    ui.confirm = AsyncMock(side_effect=_confirm)

    return ui


def make_test_agent(
    *,
    name: str = "TestAgent",
    model: str = "TestMode",
    description: str = "TestDescription",
    parameters: Sequence[Parameter] | None = None,
    feedback_function=no_feedback,
    tools: Iterable[Tool] | None = None,
    mcp_servers: list[MCPServer] | None = None,
    tool_confirmation_patterns: list[str] | None = None,
    history: list[dict] | None = None,
) -> Agent:
    return Agent(
        name=name,
        model=model,
        description=description,
        parameters=list(parameters) if parameters is not None else [],
        feedback_function=feedback_function,
        tools=list(tools) if tools is not None else [],
        mcp_servers=list(mcp_servers) if mcp_servers is not None else [],
        tool_confirmation_patterns=list(tool_confirmation_patterns) if tool_confirmation_patterns is not None else [],
        history=list(history) if history is not None else [],
    )

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


def make_ui_mock(
    *,
    ask_sequence: list[tuple[str, str]] | None = None,
    confirm_sequence: list[tuple[str, bool]] | None = None,
) -> UI:
    """
    Create a strict UI mock that validates every prompt against an expected sequence.

    Parameters:
    - ask_sequence: list of (expected_prompt, return_value) pairs; consumed in order by UI.ask.
    - confirm_sequence: list of (expected_prompt, return_value) pairs; consumed in order by UI.confirm.

    If a prompt arrives that doesn't match the next expected one or a method is
    called more times than expected, an AssertionError is raised.
    """
    ui = Mock()

    # Use local copies so tests can inspect remaining expectations after calls if needed
    ask_seq = list(ask_sequence) if ask_sequence is not None else None
    confirm_seq = list(confirm_sequence) if confirm_sequence is not None else None

    async def _ask(prompt_text: str, default: str | None = None) -> str:
        assert ask_seq is not None, "UI.ask was called but no ask_sequence was provided"
        assert len(ask_seq) > 0, "UI.ask was called more times than expected"
        expected_prompt, value = ask_seq.pop(0)
        assert (
            prompt_text == expected_prompt
        ), f"Unexpected ask prompt. Expected: {expected_prompt!r}, got: {prompt_text!r}"
        return value

    async def _confirm(prompt_text: str) -> bool:
        assert confirm_seq is not None, "UI.confirm was called but no confirm_sequence was provided"
        assert len(confirm_seq) > 0, "UI.confirm was called more times than expected"
        expected_prompt, value = confirm_seq.pop(0)
        assert (
            prompt_text == expected_prompt
        ), f"Unexpected confirm prompt. Expected: {expected_prompt!r}, got: {prompt_text!r}"
        return bool(value)

    ui.ask = AsyncMock(side_effect=_ask)
    ui.confirm = AsyncMock(side_effect=_confirm)

    # Expose remaining expectations for introspection in tests (optional)
    ui._remaining_ask_expectations = ask_seq
    ui._remaining_confirm_expectations = confirm_seq

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

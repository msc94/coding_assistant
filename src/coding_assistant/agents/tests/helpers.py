import json
from dataclasses import dataclass
from typing import Iterable, Sequence
from unittest.mock import AsyncMock, Mock

from coding_assistant.agents.parameters import Parameter
from coding_assistant.agents.types import Agent, Tool
from coding_assistant.llm.model import Completion
from coding_assistant.tools.mcp import MCPServer
from coding_assistant.ui import UI


@dataclass
class FakeFunction:
    name: str
    arguments: str


@dataclass
class FakeToolCall:
    id: str
    function: FakeFunction

    def model_dump_json(self) -> str:
        return json.dumps(
            {
                "id": self.id,
                "function": {"name": self.function.name, "arguments": self.function.arguments},
            }
        )


class FakeMessage:
    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[FakeToolCall] | None = None,
        reasoning_content: str | None = None,
    ):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls or []
        # Optional field used to simulate models that return separate reasoning content
        if reasoning_content is not None:
            self.reasoning_content = reasoning_content

    def model_dump(self):
        data: dict[str, object] = {"role": self.role}
        if self.content is not None:
            data["content"] = self.content
        if self.tool_calls:
            data["tool_calls"] = [
                {
                    "id": tc.id,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in self.tool_calls
            ]
        if hasattr(self, "reasoning_content"):
            data["reasoning_content"] = getattr(self, "reasoning_content")
        return data

    def model_dump_json(self):
        return json.dumps(self.model_dump())


class FakeCompleter:
    def __init__(self, script):
        self.script = list(script)
        self._total_tokens = 0

    async def __call__(self, messages, *, model, tools, callbacks):
        if not self.script:
            raise AssertionError("FakeCompleter script exhausted")

        action = self.script.pop(0)

        if isinstance(action, Exception):
            raise action

        text = action.model_dump_json()
        toks = len(text)
        self._total_tokens += toks

        return Completion(message=action, tokens=self._total_tokens)


def make_ui_mock(
    *,
    ask_sequence: list[tuple[str, str]] | None = None,
    confirm_sequence: list[tuple[str, bool]] | None = None,
) -> UI:
    ui = Mock()

    # Use local copies so tests can inspect remaining expectations after calls if needed
    ask_seq = list(ask_sequence) if ask_sequence is not None else None
    confirm_seq = list(confirm_sequence) if confirm_sequence is not None else None

    async def _ask(prompt_text: str, default: str | None = None) -> str:
        assert ask_seq is not None, "UI.ask was called but no ask_sequence was provided"
        assert len(ask_seq) > 0, "UI.ask was called more times than expected"
        expected_prompt, value = ask_seq.pop(0)
        assert prompt_text == expected_prompt, f"Unexpected ask prompt. Expected: {expected_prompt}, got: {prompt_text}"
        return value

    async def _confirm(prompt_text: str) -> bool:
        assert confirm_seq is not None, "UI.confirm was called but no confirm_sequence was provided"
        assert len(confirm_seq) > 0, "UI.confirm was called more times than expected"
        expected_prompt, value = confirm_seq.pop(0)
        assert (
            prompt_text == expected_prompt
        ), f"Unexpected confirm prompt. Expected: {expected_prompt}, got: {prompt_text}"
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
    parameters: Sequence[Parameter] | None = None,
    tools: Iterable[Tool] | None = None,
    history: list[dict] | None = None,
) -> Agent:
    return Agent(
        name=name,
        model=model,
        parameters=list(parameters) if parameters is not None else [],
        tools=list(tools) if tools is not None else [],
        history=list(history) if history is not None else [],
    )

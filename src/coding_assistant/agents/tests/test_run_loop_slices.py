import json

import pytest

from coding_assistant.agents.callbacks import NullCallbacks
from coding_assistant.agents.execution import run_agent_loop
from coding_assistant.agents.tests.helpers import (
    FakeFunction,
    FakeToolCall,
    FakeMessage,
    FakeCompleter,
    make_test_agent,
    no_feedback,
    make_ui_mock,
)
from coding_assistant.agents.types import Agent, TextResult, Tool
from coding_assistant.tools.tools import FinishTaskTool, ShortenConversation


"""Use shared FakeMessage/FakeCompleter from helpers."""


class FakeEchoTool(Tool):
    def __init__(self):
        self.called_with = None

    def name(self) -> str:
        return "fake.echo"

    def description(self) -> str:
        return "Echo a provided text"

    def parameters(self) -> dict:
        return {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    async def execute(self, parameters: dict) -> TextResult:
        self.called_with = parameters
        return TextResult(content=f"echo: {parameters['text']}")


@pytest.mark.asyncio
async def test_tool_selection_then_finish(monkeypatch):
    # Script: call echo tool, then finish_task
    echo_call = FakeToolCall("1", FakeFunction("fake.echo", json.dumps({"text": "hi"})))
    finish_call = FakeToolCall(
        "2",
        FakeFunction(
            "finish_task",
            json.dumps({"result": "done", "summary": "sum"}),
        ),
    )
    completer = FakeCompleter(
        [
            FakeMessage(tool_calls=[echo_call]),
            FakeMessage(tool_calls=[finish_call]),
        ]
    )

    # Pass the completer via dependency injection

    fake_tool = FakeEchoTool()

    agent = make_test_agent(tools=[fake_tool, FinishTaskTool(), ShortenConversation()])

    output = await run_agent_loop(
        agent,
        NullCallbacks(),
        shorten_conversation_at_tokens=200_000,
        no_truncate_tools=set(),
        completer=completer,
        ui=make_ui_mock(),
    )

    assert output.result == "done"
    assert output.summary == "sum"
    assert fake_tool.called_with == {"text": "hi"}
    # Ensure the tool result was appended to history
    assert any(h.get("role") == "tool" and h.get("content") == "echo: hi" for h in agent.history)


@pytest.mark.asyncio
async def test_unknown_tool_error_then_finish(monkeypatch):
    unknown_call = FakeToolCall("1", FakeFunction("unknown.tool", "{}"))
    finish_call = FakeToolCall(
        "2",
        FakeFunction(
            "finish_task",
            json.dumps({"result": "ok", "summary": "s"}),
        ),
    )
    completer = FakeCompleter(
        [
            FakeMessage(tool_calls=[unknown_call]),
            FakeMessage(tool_calls=[finish_call]),
        ]
    )

    agent = make_test_agent(tools=[FinishTaskTool(), ShortenConversation()])

    output = await run_agent_loop(
        agent,
        NullCallbacks(),
        shorten_conversation_at_tokens=200_000,
        no_truncate_tools=set(),
        completer=completer,
        ui=make_ui_mock(),
    )

    # Check that an error tool message was appended for the unknown tool
    assert any(
        h.get("role") == "tool" and str(h.get("content")).startswith("Error executing tool:") for h in agent.history
    )
    assert output.result == "ok"


@pytest.mark.asyncio
async def test_assistant_message_without_tool_calls_prompts_correction(monkeypatch):
    # First assistant message has no tool calls
    finish_call = FakeToolCall(
        "2",
        FakeFunction(
            "finish_task",
            json.dumps({"result": "r", "summary": "s"}),
        ),
    )
    completer = FakeCompleter(
        [
            FakeMessage(content="Hello"),
            FakeMessage(tool_calls=[finish_call]),
        ]
    )

    agent = make_test_agent(tools=[FinishTaskTool(), ShortenConversation()])

    output = await run_agent_loop(
        agent,
        NullCallbacks(),
        shorten_conversation_at_tokens=200_000,
        no_truncate_tools=set(),
        completer=completer,
        ui=make_ui_mock(),
    )

    # Verify the corrective user message was appended
    assert any(
        h.get("role") == "user" and "I detected a step from you without any tool calls" in h.get("content", "")
        for h in agent.history
    )
    # Assistant content should have been recorded too
    assert any(h.get("role") == "assistant" and h.get("content") == "Hello" for h in agent.history)
    assert output.result == "r"

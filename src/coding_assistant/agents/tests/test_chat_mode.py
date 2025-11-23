import json
import pytest

from coding_assistant.agents.tests.helpers import (
    FakeCompleter,
    FakeFunction,
    FakeMessage,
    FakeToolCall,
    make_test_agent,
    make_ui_mock,
)
from coding_assistant.agents.execution import run_chat_loop
from coding_assistant.agents.types import Tool, TextResult, AgentContext
from coding_assistant.agents.callbacks import NullProgressCallbacks, NullToolCallbacks


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
async def test_chat_step_prompts_user_on_no_tool_calls_once():
    # Assistant emits no tool calls -> in chat mode we should prompt the user once and append reply
    completer = FakeCompleter([FakeMessage(content="Hello")])
    desc, state = make_test_agent(tools=[], history=[{"role": "user", "content": "start"}])

    ui = make_ui_mock(ask_sequence=[("> ", "User reply")])

    # Run a single chat-loop iteration
    await run_chat_loop(
        AgentContext(desc=desc, state=state),
        agent_callbacks=NullProgressCallbacks(),
        tool_callbacks=NullToolCallbacks(),
        completer=completer,
        ui=ui,
        shorten_conversation_at_tokens=10_000,
        is_interruptible=False,
        max_iterations=1,
    )

    # Last message should be the user's reply injected by chat mode
    assert state.history[-1]["role"] == "user"
    assert state.history[-1]["content"] == "User reply"


@pytest.mark.asyncio
async def test_chat_step_executes_tools_without_prompt():
    echo_call = FakeToolCall("1", FakeFunction("fake.echo", json.dumps({"text": "hi"})))
    completer = FakeCompleter([FakeMessage(tool_calls=[echo_call])])

    echo_tool = FakeEchoTool()
    desc, state = make_test_agent(tools=[echo_tool], history=[{"role": "user", "content": "start"}])

    ui = make_ui_mock()  # no prompts expected

    await run_chat_loop(
        AgentContext(desc=desc, state=state),
        agent_callbacks=NullProgressCallbacks(),
        tool_callbacks=NullToolCallbacks(),
        completer=completer,
        ui=ui,
        shorten_conversation_at_tokens=10_000,
        is_interruptible=False,
        max_iterations=1,
    )

    # Tool must have executed
    assert echo_tool.called_with == {"text": "hi"}
    # No extra user prompt injected
    assert not any(m.get("role") == "user" and m.get("content") == "" for m in state.history)


@pytest.mark.asyncio
async def test_chat_mode_does_not_require_finish_task_tool():
    # No finish_task tool; chat mode should still allow a step
    completer = FakeCompleter([FakeMessage(content="Hi there")])
    desc, state = make_test_agent(tools=[], history=[{"role": "user", "content": "start"}])

    ui = make_ui_mock(ask_sequence=[("> ", "Ack")])

    await run_chat_loop(
        AgentContext(desc=desc, state=state),
        agent_callbacks=NullProgressCallbacks(),
        tool_callbacks=NullToolCallbacks(),
        completer=completer,
        ui=ui,
        shorten_conversation_at_tokens=10_000,
        is_interruptible=False,
        max_iterations=1,
    )

    # Should have appended the assistant message and then the user's reply
    roles = [m.get("role") for m in state.history[-2:]]
    assert roles == ["assistant", "user"]

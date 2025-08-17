import json

import pytest

from coding_assistant.agents.callbacks import NullCallbacks
from coding_assistant.agents.execution import do_single_step
from coding_assistant.agents.tests.helpers import FakeCompleter, FakeMessage, make_test_agent, make_ui_mock, no_feedback
from coding_assistant.agents.types import Agent, TextResult, Tool
from coding_assistant.tools.tools import FinishTaskTool, ShortenConversation


class DummyTool(Tool):
    def name(self):
        return "dummy"

    def description(self):
        return ""

    def parameters(self):
        return {}

    async def execute(self, parameters):
        return TextResult(content="ok")


@pytest.mark.asyncio
async def test_do_single_step_adds_shorten_prompt_on_token_threshold():
    fake_message = FakeMessage(content=("h" * 2000))
    completer = FakeCompleter([fake_message])

    agent = make_test_agent(
        tools=[DummyTool(), FinishTaskTool(), ShortenConversation()], history=[{"role": "user", "content": "start"}]
    )

    msg = await do_single_step(
        agent,
        NullCallbacks(),
        shorten_conversation_at_tokens=1000,
        no_truncate_tools=set(),
        completer=completer,
        ui=make_ui_mock(),
    )

    assert msg.content == fake_message.content

    expected_history = [
        {"role": "user", "content": "start"},
        {"role": "assistant", "content": fake_message.content},
        {
            "role": "user",
            "content": (
                "I detected a step from you without any tool calls. This is not allowed. "
                "If you want to ask the client something, please use the `ask_user` tool. "
                "If you are done with your task, please call the `finish_task` tool to signal that you are done. "
                "Otherwise, continue your work."
            ),
        },
        {
            "role": "user",
            "content": (
                "Your conversation history has grown too large. "
                "Please summarize it by using the `shorten_conversation` tool."
            ),
        },
    ]

    assert agent.history == expected_history

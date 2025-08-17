import json
import pytest

from coding_assistant.tools.tools import AskClientTool, ExecuteShellCommandTool


class FakeUI:
    def __init__(self, ask_value=None, confirm_value=None):
        self.ask_value = ask_value
        self.confirm_value = confirm_value
        self.confirm_called = 0
        self.ask_calls = []

    async def ask(self, prompt_text: str, default: str | None = None) -> str:
        self.ask_calls.append((prompt_text, default))
        return self.ask_value if self.ask_value is not None else (default or "")

    async def confirm(self, prompt_text: str) -> bool:
        self.confirm_called += 1
        return bool(self.confirm_value)


@pytest.mark.asyncio
async def test_execute_shell_command_tool_timeout():
    tool = ExecuteShellCommandTool()
    result = await tool.execute({"command": "sleep 2", "timeout": 1})
    assert "timed out" in result.content


@pytest.mark.asyncio
async def test_execute_shell_command_tool_confirmation_yes():
    tool = ExecuteShellCommandTool(shell_confirmation_patterns=["echo"], ui=FakeUI(confirm_value=True))
    result = await tool.execute({"command": "echo 'Hello'"})

    expected = {"stdout": "Hello\n", "stderr": "", "returncode": 0}
    assert json.loads(result.content) == expected


@pytest.mark.asyncio
async def test_execute_shell_command_tool_confirmation_yes_with_whitespace():
    tool = ExecuteShellCommandTool(shell_confirmation_patterns=["echo"], ui=FakeUI(confirm_value=False))
    result = await tool.execute({"command": "  echo 'Hello'"})
    assert result.content == "Command execution denied."


@pytest.mark.asyncio
async def test_execute_shell_command_tool_confirmation_no():
    tool = ExecuteShellCommandTool(shell_confirmation_patterns=["echo"], ui=FakeUI(confirm_value=False))
    result = await tool.execute({"command": "echo 'Hello'"})
    assert result.content == "Command execution denied."


@pytest.mark.asyncio
async def test_execute_shell_command_tool_no_match():
    fake_ui = FakeUI(confirm_value=True)
    tool = ExecuteShellCommandTool(shell_confirmation_patterns=["ls"], ui=fake_ui)
    result = await tool.execute({"command": "echo 'Hello'"})

    expected = {"stdout": "Hello\n", "stderr": "", "returncode": 0}
    assert json.loads(result.content) == expected
    assert fake_ui.confirm_called == 0


@pytest.mark.asyncio
async def test_ask_client_tool_enabled():
    tool = AskClientTool(enabled=True, ui=FakeUI(ask_value="yes"))
    result = await tool.execute({"question": "Do you want to proceed?", "default_answer": "no"})
    assert result.content == "yes"


@pytest.mark.asyncio
async def test_ask_client_tool_disabled():
    tool = AskClientTool(enabled=False)
    result = await tool.execute({"question": "Do you want to proceed?", "default_answer": "no"})
    assert (
        result.content
        == "Client input is disabled for this session. Please continue as if the client had given the most sensible answer to your question."
    )

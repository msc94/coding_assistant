import pytest

from coding_assistant.callbacks import (
    confirm_tool_if_needed,
    confirm_shell_if_needed,
    ConfirmationToolCallbacks,
)
from coding_assistant.agents.types import TextResult
from coding_assistant.agents.tests.helpers import make_ui_mock


@pytest.mark.asyncio
async def test_confirm_tool_if_needed_denied_and_allowed():
    tool_name = "dangerous_tool"
    arguments = {"path": "/tmp/file.txt"}
    prompt = f"Execute tool `{tool_name}` with arguments `{arguments}`?"
    ui = make_ui_mock(confirm_sequence=[(prompt, False), (prompt, True)])

    # First: denied
    res = await confirm_tool_if_needed(
        tool_name=tool_name,
        arguments=arguments,
        patterns=[r"dangerous_"],
        ui=ui,
    )
    assert isinstance(res, TextResult)
    assert res.content == "Tool execution denied."

    # Second: allowed (returns None so caller proceeds)
    res2 = await confirm_tool_if_needed(
        tool_name=tool_name,
        arguments=arguments,
        patterns=[r"dangerous_"],
        ui=ui,
    )
    assert res2 is None


@pytest.mark.asyncio
async def test_confirm_tool_if_needed_no_match_no_prompt():
    ui = make_ui_mock()  # no confirm sequence expected
    res = await confirm_tool_if_needed(
        tool_name="safe_tool",
        arguments={"x": 1},
        patterns=[r"dangerous_"],
        ui=ui,
    )
    assert res is None


@pytest.mark.asyncio
async def test_confirm_shell_if_needed_denied_and_allowed():
    tool_name = "mcp_coding_assistant_mcp_shell_execute"
    command = "rm -rf /tmp"
    args = {"command": command}
    prompt = f"Execute shell command `{command}` for tool `{tool_name}`?"
    ui = make_ui_mock(confirm_sequence=[(prompt, False), (prompt, True)])

    # Denied
    res = await confirm_shell_if_needed(
        tool_name=tool_name,
        arguments=args,
        patterns=[r"rm -rf"],
        ui=ui,
    )
    assert isinstance(res, TextResult)
    assert res.content == "Shell command execution denied."

    # Allowed
    res2 = await confirm_shell_if_needed(
        tool_name=tool_name,
        arguments=args,
        patterns=[r"rm -rf"],
        ui=ui,
    )
    assert res2 is None


@pytest.mark.asyncio
async def test_confirm_shell_if_needed_ignores_other_tools_and_bad_command():
    ui = make_ui_mock()
    # Wrong tool name -> ignored
    res = await confirm_shell_if_needed(
        tool_name="some_other_tool",
        arguments={"command": "rm -rf /tmp"},
        patterns=[r"rm -rf"],
        ui=ui,
    )
    assert res is None

    # Right tool name but command not a string -> ignored
    res2 = await confirm_shell_if_needed(
        tool_name="mcp_coding_assistant_mcp_shell_execute",
        arguments={"command": ["echo", "hi"]},
        patterns=[r"echo"],
        ui=ui,
    )
    assert res2 is None


@pytest.mark.asyncio
async def test_confirmation_tool_callbacks_tool_pattern():
    callbacks = ConfirmationToolCallbacks(
        tool_confirmation_patterns=[r"^my_tool$"],
        shell_confirmation_patterns=[r"will_not_match"],
    )
    tool_name = "my_tool"
    args = {"a": 1}
    prompt = f"Execute tool `{tool_name}` with arguments `{args}`?"
    ui = make_ui_mock(confirm_sequence=[(prompt, False), (prompt, True)])

    # Denied
    res = await callbacks.before_tool_execution(
        agent_name="Agent",
        tool_call_id="1",
        tool_name=tool_name,
        arguments=args,
        ui=ui,
    )
    assert isinstance(res, TextResult)
    assert res.content == "Tool execution denied."

    # Allowed -> returns None
    res2 = await callbacks.before_tool_execution(
        agent_name="Agent",
        tool_call_id="2",
        tool_name=tool_name,
        arguments=args,
        ui=ui,
    )
    assert res2 is None


@pytest.mark.asyncio
async def test_confirmation_tool_callbacks_shell_pattern():
    callbacks = ConfirmationToolCallbacks(
        tool_confirmation_patterns=[],
        shell_confirmation_patterns=[r"danger"],
    )
    tool_name = "mcp_coding_assistant_mcp_shell_execute"
    command = "danger cmd"
    args = {"command": command}
    prompt = f"Execute shell command `{command}` for tool `{tool_name}`?"
    ui = make_ui_mock(confirm_sequence=[(prompt, False), (prompt, True)])

    # Denied
    res = await callbacks.before_tool_execution(
        agent_name="Agent",
        tool_call_id="1",
        tool_name=tool_name,
        arguments=args,
        ui=ui,
    )
    assert isinstance(res, TextResult)
    assert res.content == "Shell command execution denied."

    # Allowed
    res2 = await callbacks.before_tool_execution(
        agent_name="Agent",
        tool_call_id="2",
        tool_name=tool_name,
        arguments=args,
        ui=ui,
    )
    assert res2 is None


@pytest.mark.asyncio
async def test_confirmation_tool_callbacks_both_patterns_shell_tool_two_prompts():
    # When both tool + shell patterns match the special shell tool, we should see two confirmations if the first is allowed.
    tool_name = "mcp_coding_assistant_mcp_shell_execute"
    command = "do something risky"
    args = {"command": command}
    tool_prompt = f"Execute tool `{tool_name}` with arguments `{args}`?"
    shell_prompt = f"Execute shell command `{command}` for tool `{tool_name}`?"
    ui = make_ui_mock(confirm_sequence=[(tool_prompt, True), (shell_prompt, False)])

    callbacks = ConfirmationToolCallbacks(
        tool_confirmation_patterns=[r"mcp_coding_assistant_mcp_shell_execute"],
        shell_confirmation_patterns=[r"risky"],
    )

    # First confirmation allowed -> second confirmation (shell) denies -> early return denial message
    res = await callbacks.before_tool_execution(
        agent_name="Agent",
        tool_call_id="1",
        tool_name=tool_name,
        arguments=args,
        ui=ui,
    )
    assert isinstance(res, TextResult)
    assert res.content == "Shell command execution denied."

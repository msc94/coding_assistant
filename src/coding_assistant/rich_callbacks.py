"""Rich/console implementations of agent callbacks.

This module contains:
  * RichAgentProgressCallbacks: pretty printing of agent progress using rich
  * ConfirmationToolCallbacks: asks the user to confirm tool (and shell) execution

Previous names: print_callbacks.PrintAgentProgressCallbacks
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING
import json
import textwrap

from rich import print
from rich.console import Group
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.pretty import Pretty

from coding_assistant.agents.callbacks import AgentProgressCallbacks, AgentToolCallbacks

if TYPE_CHECKING:  # pragma: no cover
    from coding_assistant.agents.types import ToolResult
else:
    ToolResult = object  # type: ignore


class RichAgentProgressCallbacks(AgentProgressCallbacks):
    def __init__(self, print_chunks: bool = True, print_reasoning: bool = True):
        self._print_chunks = print_chunks
        self._print_reasoning = print_reasoning

    def on_agent_start(self, agent_name: str, model: str, is_resuming: bool = False):
        status = "resuming" if is_resuming else "starting"
        print(
            Panel(
                "",
                title=f"Agent {agent_name} ({model}) {status}",
                border_style="red",
            ),
        )

    def on_agent_end(self, agent_name: str, result: str, summary: str):
        quoted_result = textwrap.indent(result, "> ", lambda _: True)
        quoted_summary = textwrap.indent(summary, "> ", lambda _: True)
        print(
            Panel(
                Markdown(f"Result\n\n{quoted_result}\n\nSummary\n\n{quoted_summary}"),
                title=f"Agent {agent_name} result",
                border_style="red",
            ),
        )

    def on_user_message(self, agent_name: str, content: str):
        print(
            Panel(
                Markdown(content),
                title=f"Agent {agent_name} user",
                border_style="blue",
            ),
        )

    def on_assistant_message(self, agent_name: str, content: str):
        print(
            Panel(
                Markdown(content),
                title=f"Agent {agent_name} assistant",
                border_style="green",
            ),
        )

    def on_assistant_reasoning(self, agent_name: str, content: str):
        if self._print_reasoning:
            print(
                Panel(
                    Markdown(content),
                    title=f"Agent {agent_name} reasoning",
                    border_style="cyan",
                ),
            )

    def _try_parse_json(self, content: str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def _format_tool_result(self, result: str):
        if data := self._try_parse_json(result):
            return Pretty(data, expand_all=True, indent_size=2)
        else:
            return Markdown(f"```\n{result}\n```")

    def on_tool_message(self, agent_name: str, tool_name: str, arguments: dict | None, result: str):
        parts: list[Any] = [Markdown(f"Name: `{tool_name}`")]

        if arguments is not None:
            parts.append(Padding(Pretty(arguments, expand_all=True, indent_size=2), (1, 0, 0, 0)))

        parts.append(Padding(self._format_tool_result(result), (1, 0, 0, 0)))

        render_group = Group(*parts)
        print(
            Panel(
                render_group,
                title=f"Agent {agent_name} tool call",
                border_style="yellow",
            ),
        )

    def on_chunk(self, chunk: str):
        if self._print_chunks:
            print(chunk, end="", flush=True)

    def on_chunks_end(self):
        if self._print_chunks:
            print()


class ConfirmationToolCallbacks(AgentToolCallbacks):
    def __init__(
        self,
        *,
        tool_confirmation_patterns: list[str] | None = None,
        shell_confirmation_patterns: list[str] | None = None,
        ui,
    ):
        import re  # local import to avoid adding to global namespace unless used

        self._re = re
        self._tool_patterns = tool_confirmation_patterns or []
        self._shell_patterns = shell_confirmation_patterns or []
        self._ui = ui

    async def before_tool_execution(
        self,
        agent_name: str,
        tool_call_id: str,
        tool_name: str,
        arguments: dict,
    ) -> Optional["ToolResult"]:
        for pat in self._tool_patterns:
            if self._re.search(pat, tool_name):
                question = f"Execute tool `{tool_name}` with arguments `{arguments}`?"
                allowed = await self._ui.confirm(question)
                if not allowed:
                    from coding_assistant.agents.types import TextResult  # local import

                    return TextResult(content="Tool execution denied.")
                break  # only ask once

        cmd = arguments.get("cmd") if isinstance(arguments, dict) else None
        if cmd and self._shell_patterns:
            for pat in self._shell_patterns:
                if self._re.search(pat, cmd):
                    question = f"Execute shell command `{cmd}` for tool `{tool_name}`?"
                    allowed = await self._ui.confirm(question)
                    if not allowed:
                        from coding_assistant.agents.types import TextResult  # local import

                        return TextResult(content="Shell command execution denied.")
                    break

        return None

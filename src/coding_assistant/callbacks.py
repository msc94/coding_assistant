from __future__ import annotations

from typing import Any, Optional
import json
import textwrap
import re

from rich import print
from rich.console import Group
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.pretty import Pretty

from coding_assistant.agents.callbacks import AgentProgressCallbacks, AgentToolCallbacks
from coding_assistant.agents.types import ToolResult, TextResult


async def confirm_tool_if_needed(*, tool_name: str, arguments: dict, patterns: list[str], ui) -> Optional[TextResult]:
    for pat in patterns:
        if re.search(pat, tool_name):
            question = f"Execute tool `{tool_name}` with arguments `{arguments}`?"
            allowed = await ui.confirm(question)
            if not allowed:
                return TextResult(content="Tool execution denied.")
            break
    return None


async def confirm_shell_if_needed(*, tool_name: str, arguments: dict, patterns: list[str], ui) -> Optional[TextResult]:
    if tool_name != "mcp_coding_assistant_mcp_shell_execute":
        return None

    command = arguments.get("command")
    if not isinstance(command, str):
        return None

    for pat in patterns:
        if re.search(pat, command):
            question = f"Execute shell command `{command}` for tool `{tool_name}`?"
            allowed = await ui.confirm(question)
            if not allowed:
                return TextResult(content="Shell command execution denied.")
            break
    return None


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

    def _format_tool_result(self, tool_name: str, result: str):
        if data := self._try_parse_json(result):
            return Pretty(data, expand_all=True, indent_size=2)
        # TODO: Avoid hard-coding tool-name prefixes to decide how to render tool results.
        # Proper solution (incremental, non-breaking):
        # 1) Add a CLI option (e.g. --markdown-tool-name-patterns) that accepts regex patterns. Thread these into
        #    RichAgentProgressCallbacks and render as Markdown when the tool_name matches any pattern.
        # 2) Keep a lightweight Markdown heuristic as a fallback when JSON parsing fails (e.g., starts with '#',
        #    contains fenced code blocks, or Markdown tables). Use conservatively to avoid mis-rendering.
        # Longer-term API improvement:
        # - Extend ToolResult with an explicit content type (e.g., content_type: "text/markdown" | "application/json"),
        #   or introduce specific result types like MarkdownResult/JsonResult/PlainTextResult so tools can declare their
        #   output type. Prefer this over name-based checks.
        # - For MCP tools, if/when the protocol exposes MIME/type hints, honor those. Otherwise rely on the configurable
        #   patterns above to mark specific MCP tools as Markdown-producing.
        # Backcompat plan:
        # - Keep this branch until configuration-based matching exists; delete this hard-coded branch once the CLI option
        #   is implemented and wired through RichAgentProgressCallbacks.
        # Example sketch:
        #   class RichAgentProgressCallbacks(..., markdown_tool_name_patterns: list[str] | None = None):
        #       self._markdown_tool_patterns = [re.compile(p) for p in (markdown_tool_name_patterns or [])]
        #   def _format_tool_result(...):
        #       if any(p.search(tool_name) for p in self._markdown_tool_patterns):
        #           return Markdown(result)
        elif tool_name.startswith("mcp_coding_assistant_mcp_todo_"):
            return Markdown(result)
        else:
            return Markdown(f"```\n{result}\n```")

    def on_tool_message(self, agent_name: str, tool_name: str, arguments: dict | None, result: str):
        parts: list[Any] = [Markdown(f"Name: `{tool_name}`")]

        if arguments is not None:
            parts.append(Padding(Pretty(arguments, expand_all=True, indent_size=2), (1, 0, 0, 0)))

        parts.append(Padding(self._format_tool_result(tool_name, result), (1, 0, 0, 0)))

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
    ):
        self._tool_patterns = tool_confirmation_patterns or []
        self._shell_patterns = shell_confirmation_patterns or []

    async def before_tool_execution(
        self,
        agent_name: str,
        tool_call_id: str,
        tool_name: str,
        arguments: dict,
        *,
        ui,
    ) -> Optional[ToolResult]:
        if result := await confirm_tool_if_needed(
            tool_name=tool_name,
            arguments=arguments,
            patterns=self._tool_patterns,
            ui=ui,
        ):
            return result

        if result := await confirm_shell_if_needed(
            tool_name=tool_name,
            arguments=arguments,
            patterns=self._shell_patterns,
            ui=ui,
        ):
            return result

        return None

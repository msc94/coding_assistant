import json
import logging

from rich import print

from coding_assistant.agents.callbacks import AgentProgressCallbacks

logger = logging.getLogger(__name__)


class DenseProgressCallbacks(AgentProgressCallbacks):
    """Dense progress callbacks with minimal formatting."""

    def __init__(self):
        pass

    def on_agent_start(self, agent_name: str, model: str, is_resuming: bool = False):
        status = "resuming" if is_resuming else "starting"
        print(f"[bold red]▸[/bold red] Agent {agent_name} ({model}) {status}")

    def on_agent_end(self, agent_name: str, result: str, summary: str):
        print(f"[bold red]◂[/bold red] Agent {agent_name} complete")
        print(f"[dim]Summary: {summary}[/dim]")

    def on_user_message(self, agent_name: str, content: str):
        print(f"[bold blue]◉[/bold blue] User: {content}")

    def on_assistant_message(self, agent_name: str, content: str):
        print(f"[bold green]◉[/bold green] Assistant: {content}")

    def on_assistant_reasoning(self, agent_name: str, content: str):
        # Don't print reasoning in dense mode
        pass

    def _count_lines(self, text: str) -> int:
        """Count number of lines in text."""
        return len(text.splitlines())

    def _format_arguments(self, arguments: dict) -> str:
        """Format arguments compactly."""
        # For large arguments, show count instead of full content
        formatted = {}
        for key, value in arguments.items():
            if isinstance(value, str) and len(value) > 100:
                formatted[key] = f"<{len(value)} chars>"
            else:
                formatted[key] = value
        return json.dumps(formatted, indent=None)

    def on_tool_message(self, agent_name: str, tool_name: str, arguments: dict | None, result: str):
        # Print tool name and arguments
        args_str = self._format_arguments(arguments) if arguments else "{}"
        print(f"[bold yellow]▸[/bold yellow] {tool_name}({args_str})")

        # Print result summary (just line count)
        line_count = self._count_lines(result)
        print(f"[dim]  → {line_count} lines[/dim]")

    def on_chunk(self, chunk: str):
        # Always print chunks in dense mode
        print(chunk, end="", flush=True)

    def on_chunks_end(self):
        print()  # Newline after chunks

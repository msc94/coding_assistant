from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from coding_assistant.agents.types import ToolResult  # for type hints only
else:  # At runtime we avoid importing to prevent circular import
    ToolResult = object  # type: ignore


class AgentProgressCallbacks(ABC):
    """Abstract interface for agent callbacks."""

    @abstractmethod
    def on_agent_start(self, agent_name: str, model: str, is_resuming: bool = False):
        """Handle agent start events."""
        pass

    @abstractmethod
    def on_agent_end(self, agent_name: str, result: str, summary: str):
        """Handle agent end events."""
        pass

    @abstractmethod
    def on_user_message(self, agent_name: str, content: str):
        """Handle messages with role: user."""
        pass

    @abstractmethod
    def on_assistant_message(self, agent_name: str, content: str):
        """Handle messages with role: assistant."""
        pass

    @abstractmethod
    def on_assistant_reasoning(self, agent_name: str, content: str):
        """Handle reasoning content from assistant."""
        pass

    @abstractmethod
    def on_tool_message(self, agent_name: str, tool_name: str, arguments: dict | None, result: str):
        """Handle messages with role: tool."""
        pass

    @abstractmethod
    def on_chunk(self, chunk: str):
        """Handle LLM chunks."""
        pass

    @abstractmethod
    def on_chunks_end(self):
        """Handle end of LLM chunks."""
        pass


class NullProgressCallbacks(AgentProgressCallbacks):
    """Null object implementation that does nothing."""

    def on_agent_start(self, agent_name: str, model: str, is_resuming: bool = False):
        pass

    def on_agent_end(self, agent_name: str, result: str, summary: str):
        pass

    def on_user_message(self, agent_name: str, content: str):
        pass

    def on_assistant_message(self, agent_name: str, content: str):
        pass

    def on_assistant_reasoning(self, agent_name: str, content: str):
        pass

    def on_tool_message(self, agent_name: str, tool_name: str, arguments: dict | None, result: str):
        pass

    def on_chunk(self, chunk: str):
        pass

    def on_chunks_end(self):
        pass


class AgentToolCallbacks(ABC):
    @abstractmethod
    async def before_tool_execution(
        self,
        agent_name: str,
        tool_call_id: str,
        tool_name: str,
        arguments: dict,
    ) -> Optional[ToolResult]:  # pragma: no cover - interface
        pass


class NullToolCallbacks(AgentToolCallbacks):
    async def before_tool_execution(self, agent_name: str, tool_call_id: str, tool_name: str, arguments: dict) -> None:  # type: ignore[override]
        return None


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
        # Tool-level confirmation
        for pat in self._tool_patterns:
            if self._re.search(pat, tool_name):
                question = f"Execute tool `{tool_name}` with arguments `{arguments}`?"
                allowed = await self._ui.confirm(question)
                if not allowed:
                    from coding_assistant.agents.types import TextResult  # local import
                    return TextResult(content="Tool execution denied.")
                break  # only ask once

        # Shell command confirmation (if a 'cmd' argument exists)
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

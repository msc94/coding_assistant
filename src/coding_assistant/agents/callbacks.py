"""Callback interfaces for agent interactions."""

import json
import textwrap
from abc import ABC, abstractmethod
from pprint import pformat
from typing import Any


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

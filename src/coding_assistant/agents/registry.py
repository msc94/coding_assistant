"""Tool registry system for managing agent tools."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Abstract base class for agent tools."""
    
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def parameters(self) -> dict: ...

    @abstractmethod
    async def execute(self, parameters: dict) -> str: ...


class ToolRegistry:
    """Registry for managing agent tools."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._tool_factories: Dict[str, Callable[..., Tool]] = {}
    
    def register_tool(self, tool: Tool):
        """Register a tool instance."""
        if tool.name().startswith("mcp_"):
            raise RuntimeError("Tools cannot start with mcp_")
        
        self._tools[tool.name()] = tool
        logger.debug(f"Registered tool: {tool.name()}")
    
    def register_tool_factory(self, name: str, factory: Callable[..., Tool]):
        """Register a tool factory for dynamic tool creation."""
        self._tool_factories[name] = factory
        logger.debug(f"Registered tool factory: {name}")
    
    def create_tool(self, name: str, *args, **kwargs) -> Tool:
        """Create a tool using a registered factory."""
        if name not in self._tool_factories:
            raise RuntimeError(f"Tool factory {name} not found")
        
        tool = self._tool_factories[name](*args, **kwargs)
        return tool
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_tool_definitions(self) -> List[dict]:
        """Get tool definitions for LLM API."""
        definitions = []
        for tool in self._tools.values():
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool.name(),
                    "description": tool.description(),
                    "parameters": tool.parameters(),
                },
            })
        return definitions
    
    async def execute_tool(self, name: str, parameters: dict) -> str:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            raise RuntimeError(f"Tool {name} not found in registry")
        
        return await tool.execute(parameters)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())


class AgentToolRegistry(ToolRegistry):
    """Extended tool registry with agent-specific functionality."""
    
    def __init__(self, agent_factory: Optional[Callable] = None):
        super().__init__()
        self._agent_factory = agent_factory
    
    def set_agent_factory(self, factory: Callable):
        """Set the agent factory for creating sub-agents."""
        self._agent_factory = factory
    
    def create_agent(self, *args, **kwargs):
        """Create an agent using the registered factory."""
        if not self._agent_factory:
            raise RuntimeError("No agent factory registered")
        return self._agent_factory(*args, **kwargs)

"""New main entry point using the refactored architecture."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from opentelemetry import trace
from rich.panel import Panel
from rich import print as rich_print

from coding_assistant.agents.orchestration import AgentOrchestrator
from coding_assistant.agents.callbacks import AgentCallbacks, RichCallbacks
from coding_assistant.config import Config
from coding_assistant.cache import save_orchestrator_history, save_conversation_summary

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


async def run_orchestrator_agent(
    task: str,
    config: Config,
    mcp_servers: list,
    history: list | None,
    conversation_summaries: list[str],
    instructions: str | None,
    working_directory: Path,
    agent_callbacks: AgentCallbacks,
):
    """Run orchestrator agent using the new architecture."""
    with tracer.start_as_current_span("run_orchestrator_agent_new"):
        # Create orchestrator
        orchestrator = AgentOrchestrator(
            config=config,
            mcp_servers=mcp_servers,
            agent_callbacks=agent_callbacks,
        )
        
        # Create orchestrator agent
        agent = await orchestrator.create_orchestrator_agent(
            task=task,
            summaries=conversation_summaries[-5:] if conversation_summaries else [],
            instructions=instructions,
            history=history,
        )
        
        try:
            # Run agent to completion
            output = await orchestrator.run_agent(agent)
        finally:
            # Save history
            save_orchestrator_history(working_directory, agent.history)
        
        # Save summary
        save_conversation_summary(working_directory, output.summary)
        
        # Display result
        rich_print(
            Panel(
                f"Result: {output.result}\n\nSummary: {output.summary}",
                title="🎉 Final Result",
                border_style="bright_green",
            )
        )
        
        return output.result


class OrchestratorToolCompat:
    """Compatibility wrapper for the old OrchestratorTool interface."""
    
    def __init__(
        self,
        config: Config,
        mcp_servers: list | None = None,
        history: list | None = None,
        agent_callbacks: Optional[AgentCallbacks] = None,
    ):
        self._config = config
        self._mcp_servers = mcp_servers or []
        self._history = history or []
        self._agent_callbacks = agent_callbacks or RichCallbacks()
        self.history = self._history
        self.summary = ""
    
    async def execute(self, parameters: dict) -> str:
        """Execute orchestrator using new architecture."""
        # Create orchestrator
        orchestrator = AgentOrchestrator(
            config=self._config,
            mcp_servers=self._mcp_servers,
            agent_callbacks=self._agent_callbacks,
        )
        
        # Create and run orchestrator agent
        agent = await orchestrator.create_orchestrator_agent(
            task=parameters["task"],
            summaries=parameters.get("summaries", []),
            instructions=parameters.get("instructions"),
            history=self._history,
        )
        
        output = await orchestrator.run_agent(agent)
        
        # Update compatibility fields
        self.history = agent.history
        self.summary = output.summary
        
        return output.result

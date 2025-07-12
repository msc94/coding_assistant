"""Agent orchestration and coordination."""

import asyncio
from typing import Optional, List, Callable

from coding_assistant.agents.agent import Agent, AgentOutput, fill_parameters
from coding_assistant.agents.engine import AgentEngine, AgentExecutionContext
from coding_assistant.agents.registry import AgentToolRegistry
from coding_assistant.agents.callbacks import AgentCallbacks, NullCallbacks
from coding_assistant.config import Config


class AgentOrchestrator:
    """Coordinates agent creation and execution."""
    
    def __init__(
        self,
        config: Config,
        mcp_servers: list,
        agent_callbacks: Optional[AgentCallbacks] = None,
    ):
        self.config = config
        self.mcp_servers = mcp_servers
        self.agent_callbacks = agent_callbacks or NullCallbacks()
        
        # Create execution context
        self.tool_registry = AgentToolRegistry()
        self.execution_context = AgentExecutionContext(self.tool_registry, mcp_servers)
        self.engine = AgentEngine(self.execution_context)
        
        # Set up agent factory
        self.tool_registry.set_agent_factory(self._create_agent)
        
        # Register core tools
        self._register_core_tools()
    
    def _register_core_tools(self):
        """Register core agent tools."""
        from coding_assistant.agents.tools import (
            FinishTaskTool,
            ShortenConversationTool,
            AskClientTool,
            ExecuteShellCommandTool,
            AgentTool,
            FeedbackTool,
        )
        
        # Register lifecycle tools (these will be added per-agent)
        self.tool_registry.register_tool_factory("finish_task", FinishTaskTool)
        self.tool_registry.register_tool_factory("shorten_conversation", ShortenConversationTool)
        
        # Register utility tools
        self.tool_registry.register_tool(AskClientTool())
        self.tool_registry.register_tool(ExecuteShellCommandTool())
        
        # Register agent coordination tools
        self.tool_registry.register_tool(AgentTool(
            config=self.config,
            orchestrator=self,
            agent_callbacks=self.agent_callbacks,
        ))
        
        self.tool_registry.register_tool(FeedbackTool(
            config=self.config,
            orchestrator=self,
            agent_callbacks=self.agent_callbacks,
        ))
    
    def _create_agent(
        self,
        name: str,
        model: str,
        description: str,
        parameters: list,
        feedback_function: Callable,
        tools: Optional[List[str]] = None,
        history: Optional[list] = None,
    ) -> Agent:
        """Create an agent with the specified configuration."""
        agent = Agent(
            name=name,
            model=model,
            description=description,
            parameters=parameters,
            feedback_function=feedback_function,
            history=history or [],
        )
        
        # Add lifecycle tools specific to this agent
        self.tool_registry.register_tool(
            self.tool_registry.create_tool("finish_task", agent)
        )
        self.tool_registry.register_tool(
            self.tool_registry.create_tool("shorten_conversation", agent)
        )
        
        return agent
    
    async def create_orchestrator_agent(
        self,
        task: str,
        summaries: Optional[List[str]] = None,
        instructions: Optional[str] = None,
        history: Optional[list] = None,
    ) -> Agent:
        """Create an orchestrator agent."""
        parameters = fill_parameters(
            parameter_description={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The task to assign to the orchestrator agent.",
                    },
                    "summaries": {
                        "type": "array",
                        "description": "The past conversation summaries of the client and the agent.",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Special instructions for the agent.",
                    },
                },
                "required": ["task"],
            },
            parameter_values={
                "task": task,
                "summaries": summaries or [],
                "instructions": instructions,
            },
        )
        
        async def feedback_function(agent: Agent) -> str | None:
            return await self._get_feedback(
                agent,
                ask_user_for_feedback=self.config.enable_user_feedback,
                ask_agent_for_feedback=self.config.enable_feedback_agent,
            )
        
        description = "Launch an orchestrator agent to accomplish a given task. The agent can delegate tasks to other agents where it sees fit."
        
        return self._create_agent(
            name="Orchestrator",
            model=self.config.expert_model,
            description=description,
            parameters=parameters,
            feedback_function=feedback_function,
            history=history,
        )
    
    async def create_research_agent(
        self,
        task: str,
        expected_output: str,
        instructions: Optional[str] = None,
        expert_knowledge: bool = False,
    ) -> Agent:
        """Create a research/development agent."""
        parameters = fill_parameters(
            parameter_description={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The task to assign to the sub-agent."},
                    "expected_output": {"type": "string", "description": "The expected output format."},
                    "instructions": {"type": "string", "description": "Special instructions for the agent."},
                    "expert_knowledge": {"type": "boolean", "description": "Use expert-level agent."},
                },
                "required": ["task", "expected_output"],
            },
            parameter_values={
                "task": task,
                "expected_output": expected_output,
                "instructions": instructions,
                "expert_knowledge": expert_knowledge,
            },
        )
        
        model = self.config.expert_model if expert_knowledge else self.config.model
        
        async def feedback_function(agent: Agent) -> str | None:
            return await self._get_feedback(
                agent,
                ask_user_for_feedback=self.config.enable_user_feedback,
                ask_agent_for_feedback=self.config.enable_feedback_agent,
            )
        
        description = "Launch a sub-agent to work on a given task. The agent will refuse to accept any tasks that are not clearly defined and miss context."
        
        return self._create_agent(
            name="Agent",
            model=model,
            description=description,
            parameters=parameters,
            feedback_function=feedback_function,
        )
    
    async def run_agent(
        self,
        agent: Agent,
        shorten_conversation_at_tokens: int = 100_000,
    ) -> AgentOutput:
        """Run an agent to completion."""
        return await self.engine.run_agent(
            agent,
            self.agent_callbacks,
            shorten_conversation_at_tokens,
        )
    
    async def _get_feedback(
        self,
        agent: Agent,
        ask_user_for_feedback: bool,
        ask_agent_for_feedback: bool,
    ) -> str | None:
        """Get feedback for an agent's output."""
        if not agent.output:
            raise ValueError("Agent has no result to provide feedback on.")
        
        if ask_agent_for_feedback:
            # Use feedback tool to get agent feedback
            feedback_tool = self.tool_registry.get_tool("launch_feedback_agent")
            if feedback_tool:
                from coding_assistant.agents.agent import format_parameters
                formatted_parameters = format_parameters(agent.parameters)
                agent_feedback = await feedback_tool.execute({
                    "description": agent.description,
                    "parameters": "\n" + formatted_parameters,
                    "result": agent.output.result,
                    "summary": agent.output.summary,
                    "feedback": agent.output.feedback,
                })
            else:
                agent_feedback = "Ok"
        else:
            agent_feedback = "Ok"
        
        if ask_user_for_feedback:
            from rich.prompt import Prompt
            feedback = await asyncio.to_thread(
                Prompt.ask, f"Feedback for {agent.name}", default=agent_feedback
            )
        else:
            feedback = agent_feedback
        
        return None if feedback == "Ok" else feedback

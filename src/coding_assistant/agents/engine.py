"""Agent execution engine - pure execution logic separated from agent data structures."""

import json
import logging
import textwrap
from typing import Optional

from opentelemetry import trace

from coding_assistant.agents.callbacks import AgentCallbacks
from coding_assistant.llm.model import complete

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

FEEDBACK_TEMPLATE = """
Your client has provided the following feedback on your work:

{feedback}

Please rework your result to address the feedback.
Afterwards, call the `finish_task` tool again to signal that you are done.
""".strip()


class AgentExecutionContext:
    """Context for agent execution that handles tool registry and state management."""
    
    def __init__(self, tool_registry: "ToolRegistry", mcp_servers: list):
        self.tool_registry = tool_registry
        self.mcp_servers = mcp_servers
    
    async def get_available_tools(self) -> list:
        """Get all available tools for the agent."""
        tools = []
        
        # Get tools from registry
        tools.extend(self.tool_registry.get_tool_definitions())
        
        # Get MCP server tools
        tools.extend(await self._get_mcp_tools())
        
        return tools
    
    async def _get_mcp_tools(self) -> list:
        """Get tools from MCP servers."""
        tools = []
        for server in self.mcp_servers:
            for _, tool_list in await server.session.list_tools():
                for tool in tool_list or []:
                    tool_id = f"mcp_{server.name}_{tool.name}"
                    
                    # Fix input schema for compatibility
                    self._fix_input_schema(tool.inputSchema)
                    
                    tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tool_id,
                                "description": tool.description,
                                "parameters": tool.inputSchema,
                            },
                        }
                    )
        return tools
    
    def _fix_input_schema(self, input_schema: dict):
        """Fix input schema to be compatible with Gemini API."""
        for property in input_schema.get("properties", {}).values():
            if (format := property.get("format")) and format == "uri":
                property.pop("format", None)
    
    async def execute_tool_call(self, tool_call, agent_callbacks: AgentCallbacks, agent_name: str) -> str:
        """Execute a tool call and return the result."""
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments or "{}")
        
        trace.get_current_span().set_attribute("function.name", function_name)
        trace.get_current_span().set_attribute("function.args", tool_call.function.arguments)
        
        if function_name.startswith("mcp_"):
            result = await self._handle_mcp_tool_call(function_name, function_args)
        else:
            result = await self.tool_registry.execute_tool(function_name, function_args)
        
        trace.get_current_span().set_attribute("function.result", result)
        
        # Limit result size
        if len(result) > 50_000:
            result = "System error: Tool call result too long. Please try again with different parameters."
        
        agent_callbacks.on_tool_message(agent_name, function_name, function_args, result)
        
        return result
    
    async def _handle_mcp_tool_call(self, function_name: str, arguments: dict) -> str:
        """Handle MCP tool calls."""
        parts = function_name.split("_")
        assert parts[0] == "mcp"
        
        server_name = parts[1]
        tool_name = "_".join(parts[2:])
        
        for server in self.mcp_servers:
            if server.name == server_name:
                result = await server.session.call_tool(tool_name, arguments)
                if not result.content:
                    return "MCP server did not return any content."
                return result.content[0].text
        
        raise RuntimeError(f"Server {server_name} not found in MCP servers.")


class AgentEngine:
    """Core agent execution engine."""
    
    def __init__(self, execution_context: AgentExecutionContext):
        self.execution_context = execution_context
    
    @tracer.start_as_current_span("execute_single_step")
    async def execute_single_step(
        self, 
        agent: "Agent", 
        agent_callbacks: AgentCallbacks, 
        shorten_conversation_at_tokens: int
    ) -> "CompletionMessage":
        """Execute a single step of agent conversation."""
        trace.get_current_span().set_attribute("agent.name", agent.name)
        
        # Validate agent has required tools
        if not self.execution_context.tool_registry.has_tool("finish_task"):
            raise RuntimeError("Agent needs to have a `finish_task` tool in order to run a step.")
        
        # Get available tools
        tools = await self.execution_context.get_available_tools()
        trace.get_current_span().set_attribute("agent.tools", json.dumps(tools))
        
        # Validate agent has history
        if not agent.history:
            raise RuntimeError("Agent needs to have history in order to run a step.")
        
        trace.get_current_span().set_attribute("agent.history", json.dumps(agent.history))
        
        # Get completion from LLM
        completion = await complete(agent.history, model=agent.model, tools=tools)
        message = completion.message
        
        trace.get_current_span().set_attribute("completion.message", message.model_dump_json())
        
        # Clean up reasoning content
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            trace.get_current_span().set_attribute("completion.reasoning_content", message.reasoning_content)
            del message.reasoning_content
        
        # Add assistant message to history
        self._append_assistant_message(agent.history, agent_callbacks, agent.name, message)
        
        # Handle tool calls
        for tool_call in message.tool_calls or []:
            result = await self.execution_context.execute_tool_call(tool_call, agent_callbacks, agent.name)
            self._append_tool_message(
                agent.history, tool_call.id, tool_call.function.name, result
            )
        
        # Handle no tool calls
        if not message.tool_calls:
            self._append_user_message(
                agent.history,
                agent_callbacks,
                agent.name,
                "I detected a step from you without any tool calls. This is not allowed. If you want to ask the client something, please use the `ask_user` tool. Otherwise, please call the `finish_task` tool to signal that you are done.",
            )
        
        # Handle conversation length
        if completion.tokens > shorten_conversation_at_tokens and not agent.shortened_conversation:
            self._append_user_message(
                agent.history,
                agent_callbacks,
                agent.name,
                "Your conversation is becoming too long. Please call `shorten_conversation` to trim it.",
            )
        
        return message
    
    @tracer.start_as_current_span("run_agent")
    async def run_agent(
        self,
        agent: "Agent",
        agent_callbacks: AgentCallbacks,
        shorten_conversation_at_tokens: int = 100_000,
    ) -> "AgentOutput":
        """Run an agent to completion."""
        if agent.output:
            raise RuntimeError("Agent already has a result or summary.")
        
        trace.get_current_span().set_attribute("agent.name", agent.name)
        
        # Initialize agent if needed
        if not agent.history:
            start_message = agent.create_start_message()
            self._append_user_message(agent.history, agent_callbacks, agent.name, start_message)
            agent_callbacks.on_agent_start(agent.name, agent.model, is_resuming=False)
        else:
            agent_callbacks.on_agent_start(agent.name, agent.model, is_resuming=True)
        
        while True:
            # Execute until agent produces output
            while not agent.output:
                await self.execute_single_step(agent, agent_callbacks, shorten_conversation_at_tokens)
                
                # Handle conversation shortening
                if agent.shortened_conversation:
                    agent.history = []
                    start_message = agent.create_start_message()
                    self._append_user_message(agent.history, agent_callbacks, agent.name, start_message)
                    self._append_user_message(
                        agent.history,
                        agent_callbacks,
                        agent.name,
                        f"A summary of your conversation with the client until now:\n\n{agent.shortened_conversation}\n\nPlease continue your work.",
                    )
                    agent.shortened_conversation = None
            
            trace.get_current_span().set_attribute("agent.result", agent.output.result)
            trace.get_current_span().set_attribute("agent.summary", agent.output.summary)
            
            agent_callbacks.on_agent_end(agent.name, agent.output.result, agent.output.summary)
            
            # Handle feedback
            if feedback := await agent.feedback_function(agent):
                formatted_feedback = FEEDBACK_TEMPLATE.format(
                    feedback=textwrap.indent(feedback, "  "),
                )
                self._append_user_message(agent.history, agent_callbacks, agent.name, formatted_feedback)
                agent.output = None
            else:
                break
        
        if not agent.output:
            raise RuntimeError("Agent finished without a result.")
        
        return agent.output
    
    def _append_user_message(self, history: list, callbacks: AgentCallbacks, agent_name: str, content: str):
        """Add user message to history."""
        callbacks.on_user_message(agent_name, content)
        history.append({"role": "user", "content": content})
    
    def _append_assistant_message(self, history: list, callbacks: AgentCallbacks, agent_name: str, message):
        """Add assistant message to history."""
        if message.content:
            callbacks.on_assistant_message(agent_name, message.content)
        history.append(message.model_dump())
    
    def _append_tool_message(self, history: list, tool_call_id: str, function_name: str, result: str):
        """Add tool message to history."""
        history.append({
            "tool_call_id": tool_call_id,
            "role": "tool",
            "name": function_name,
            "content": result,
        })

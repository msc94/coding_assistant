"""Agent tools with clean separation of concerns."""

import asyncio
import subprocess
from typing import Optional, TYPE_CHECKING

from rich.prompt import Prompt

from coding_assistant.agents.registry import Tool
from coding_assistant.agents.agent import Agent, AgentOutput, fill_parameters
from coding_assistant.agents.callbacks import AgentCallbacks, NullCallbacks
from coding_assistant.config import Config

if TYPE_CHECKING:
    from coding_assistant.agents.orchestration import AgentOrchestrator


class FinishTaskTool(Tool):
    """Tool for signaling task completion."""
    
    def __init__(self, agent: Agent):
        self._agent = agent
    
    def name(self) -> str:
        return "finish_task"
    
    def description(self) -> str:
        return "Signals that the assigned task is complete. This tool must be called eventually to terminate the agent's execution loop."
    
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                    "description": "The result of the work on the task. The work of the agent is evaluated based on this result.",
                },
                "summary": {
                    "type": "string",
                    "description": "A concise summary of the conversation the agent and the client had.",
                },
                "feedback": {
                    "type": "string",
                    "description": "A summary of the feedback given by the client to the agent during the task.",
                },
            },
            "required": ["result", "summary"],
        }
    
    async def execute(self, parameters: dict) -> str:
        self._agent.set_output(
            result=parameters["result"],
            summary=parameters["summary"],
            feedback=parameters.get("feedback"),
        )
        return "Agent output set."


class ShortenConversationTool(Tool):
    """Tool for shortening conversation history."""
    
    def __init__(self, agent: Agent):
        self._agent = agent
    
    def name(self) -> str:
        return "shorten_conversation"
    
    def description(self) -> str:
        return "Give the framework a short, concise summary of your conversation with the client so far. This tool should only be called when the client tells you to call it."
    
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A summary of the conversation so far.",
                },
            },
            "required": ["summary"],
        }
    
    async def execute(self, parameters: dict) -> str:
        self._agent.set_shortened_conversation(parameters["summary"])
        return "Shortened conversation set."


class AskClientTool(Tool):
    """Tool for asking the user for input."""
    
    def name(self) -> str:
        return "ask_user"
    
    def description(self) -> str:
        return "Ask the user for input."
    
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the client.",
                },
                "default_answer": {
                    "type": "string",
                    "description": "A sensible default answer to the question.",
                },
            },
            "required": ["question"],
        }
    
    async def execute(self, parameters: dict) -> str:
        question = parameters["question"]
        default_answer = parameters.get("default_answer")
        answer = await asyncio.to_thread(Prompt.ask, question, default=default_answer)
        return str(answer)


class ExecuteShellCommandTool(Tool):
    """Tool for executing shell commands."""
    
    def name(self) -> str:
        return "execute_shell_command"
    
    def description(self) -> str:
        return (
            "Execute a shell command and return the output. The command will be executed in bash. Examples for commands are:\n"
            "- `eza` or `ls` for listing files in a directory\n"
            "- `git` for running git commands\n"
            "- `fd` or `find` for searching files\n"
            "- `rg` or `grep` for searching text in files\n"
            "- `gh` for interfacing with GitHub\n"
        )
    
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
            },
            "required": ["command"],
        }
    
    async def execute(self, parameters: dict) -> str:
        command = parameters["command"]
        args = ["bash", "-c", command]
        result = await asyncio.to_thread(subprocess.run, args, capture_output=True, text=True)
        
        if result.returncode != 0:
            return (
                f"Command failed with error code {result.returncode}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
        
        return result.stdout


class AgentTool(Tool):
    """Tool for launching sub-agents."""
    
    def __init__(
        self,
        config: Config,
        orchestrator: "AgentOrchestrator",
        agent_callbacks: Optional[AgentCallbacks] = None,
    ):
        self._config = config
        self._orchestrator = orchestrator
        self._agent_callbacks = agent_callbacks or NullCallbacks()
    
    def name(self) -> str:
        return "launch_research_agent"
    
    def description(self) -> str:
        return "Launch a sub-agent to work on a given task. Examples for tasks are researching a topic or question, or developing a feature according to an implementation plan."
    
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task to assign to the sub-agent.",
                },
                "expected_output": {
                    "type": "string",
                    "description": "The expected output to return to the client.",
                },
                "instructions": {
                    "type": "string",
                    "description": "Special instructions for the agent.",
                },
                "expert_knowledge": {
                    "type": "boolean",
                    "description": "Should only be set to true when the task is extraordinarily difficult.",
                },
            },
            "required": ["task", "expected_output"],
        }
    
    async def execute(self, parameters: dict) -> str:
        agent = await self._orchestrator.create_research_agent(
            task=parameters["task"],
            expected_output=parameters["expected_output"],
            instructions=parameters.get("instructions"),
            expert_knowledge=parameters.get("expert_knowledge", False),
        )
        
        output = await self._orchestrator.run_agent(agent)
        return output.result


class FeedbackTool(Tool):
    """Tool for launching feedback agents."""
    
    def __init__(
        self,
        config: Config,
        orchestrator: "AgentOrchestrator",
        agent_callbacks: Optional[AgentCallbacks] = None,
    ):
        self._config = config
        self._orchestrator = orchestrator
        self._agent_callbacks = agent_callbacks or NullCallbacks()
    
    def name(self) -> str:
        return "launch_feedback_agent"
    
    def description(self) -> str:
        return "Launch a feedback agent that provides feedback on the output of another agent."
    
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "The description of the agent."},
                "parameters": {"type": "string", "description": "The parameters the agent was given."},
                "result": {"type": "string", "description": "The result of the agent."},
                "summary": {"type": "string", "description": "A summary of the conversation."},
                "feedback": {"type": "string", "description": "The feedback provided to the agent."},
            },
            "required": ["description", "parameters", "result"],
        }
    
    async def execute(self, parameters: dict) -> str:
        # Create feedback agent parameters
        feedback_parameters = fill_parameters(
            parameter_description=self.parameters(),
            parameter_values=parameters,
        )
        
        # Create feedback agent with simple feedback function
        async def no_feedback(agent: Agent) -> str | None:
            return None
        
        feedback_agent = Agent(
            name="Feedback",
            model=self._config.model,
            description=self.description(),
            parameters=feedback_parameters,
            feedback_function=no_feedback,
        )
        
        output = await self._orchestrator.run_agent(feedback_agent)
        return output.result

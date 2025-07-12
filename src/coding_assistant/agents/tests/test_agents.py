"""Test the refactored agent architecture."""
from unittest.mock import MagicMock, patch
import pytest

from coding_assistant.agents.agent import Agent, fill_parameters
from coding_assistant.agents.orchestration import AgentOrchestrator
from coding_assistant.agents.main_compat import OrchestratorToolCompat
from coding_assistant.agents.callbacks import NullCallbacks
from coding_assistant.config import Config

TEST_MODEL = "gemini/gemini-2.5-pro"


def create_test_config() -> Config:
    """Helper function to create a test Config with all required parameters."""
    return Config(
        model=TEST_MODEL,
        expert_model=TEST_MODEL,
        enable_feedback_agent=False,  # Disable to avoid complex setup
        enable_user_feedback=False,
        instructions=None,
        sandbox_directories=[],
        mcp_servers=[],
    )


@pytest.mark.asyncio
async def test_agent_creation():
    """Test basic agent creation."""
    config = create_test_config()
    orchestrator = AgentOrchestrator(
        config=config,
        mcp_servers=[],
        agent_callbacks=NullCallbacks(),
    )
    
    agent = await orchestrator.create_orchestrator_agent(
        task="Test task",
        instructions="Test instructions",
    )
    
    assert agent.name == "Orchestrator"
    assert agent.model == TEST_MODEL
    assert len(agent.parameters) > 0
    assert agent.output is None


@pytest.mark.asyncio
async def test_agent_parameter_filling():
    """Test parameter filling functionality."""
    parameter_description = {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "The task"},
            "optional": {"type": "string", "description": "Optional param"},
        },
        "required": ["task"],
    }
    
    parameter_values = {
        "task": "Test task",
    }
    
    parameters = fill_parameters(parameter_description, parameter_values)
    
    assert len(parameters) == 1
    assert parameters[0].name == "task"
    assert parameters[0].value == "Test task"


@pytest.mark.asyncio
async def test_agent_state_management():
    """Test agent state management methods."""
    # Create mock feedback function
    async def mock_feedback(agent):
        return None
    
    agent = Agent(
        name="Test",
        model=TEST_MODEL,
        description="Test agent",
        parameters=[],
        feedback_function=mock_feedback,
    )
    
    # Test output setting
    agent.set_output("Test result", "Test summary", "Test feedback")
    assert agent.output is not None
    assert agent.output.result == "Test result"
    assert agent.output.summary == "Test summary"
    assert agent.output.feedback == "Test feedback"
    
    # Test output reset
    agent.reset_output()
    assert agent.output is None
    
    # Test conversation shortening
    agent.set_shortened_conversation("Test summary")
    assert agent.shortened_conversation == "Test summary"


@pytest.mark.asyncio
async def test_orchestrator_tool_compat_basic():
    """Test compatibility layer for OrchestratorTool."""
    config = create_test_config()
    
    tool = OrchestratorToolCompat(
        config=config,
        mcp_servers=[],
        agent_callbacks=NullCallbacks(),
    )
    
    assert hasattr(tool, 'execute')
    assert hasattr(tool, 'history')
    assert hasattr(tool, 'summary')


def test_agent_start_message():
    """Test agent start message creation."""
    async def mock_feedback(agent):
        return None
    
    agent = Agent(
        name="TestAgent",
        model=TEST_MODEL,
        description="A test agent",
        parameters=[],
        feedback_function=mock_feedback,
    )
    
    message = agent.create_start_message()
    assert "TestAgent" in message
    assert "A test agent" in message


def test_parameter_filling_required_missing():
    """Test parameter filling with missing required parameter."""
    parameter_description = {
        "type": "object",
        "properties": {
            "required_param": {"type": "string", "description": "Required parameter"},
        },
        "required": ["required_param"],
    }
    
    parameter_values = {}
    
    with pytest.raises(RuntimeError, match="Parameter required_param is required"):
        fill_parameters(parameter_description, parameter_values)


def test_parameter_filling_array_type():
    """Test parameter filling with array type."""
    parameter_description = {
        "type": "object",
        "properties": {
            "list_param": {"type": "array", "description": "List parameter"},
        },
        "required": ["list_param"],
    }
    
    parameter_values = {
        "list_param": ["item1", "item2", "item3"]
    }
    
    parameters = fill_parameters(parameter_description, parameter_values)
    
    assert len(parameters) == 1
    assert parameters[0].name == "list_param"
    assert "- item1" in parameters[0].value
    assert "- item2" in parameters[0].value
    assert "- item3" in parameters[0].value


def test_parameter_filling_boolean_type():
    """Test parameter filling with boolean type."""
    parameter_description = {
        "type": "object",
        "properties": {
            "bool_param": {"type": "boolean", "description": "Boolean parameter"},
        },
        "required": ["bool_param"],
    }
    
    parameter_values = {
        "bool_param": True
    }
    
    parameters = fill_parameters(parameter_description, parameter_values)
    
    assert len(parameters) == 1
    assert parameters[0].name == "bool_param"
    assert parameters[0].value == "True"

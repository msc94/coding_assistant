"""Agent data structures and lifecycle management."""

import dataclasses
import textwrap
from dataclasses import dataclass, field
from typing import Callable, Optional, List
import json

PARAMETER_TEMPLATE = """
Name: {name}
Description: {description}
Value: {value}
""".strip()

START_MESSAGE_TEMPLATE = """
You are an agent named `{name}`.

## Task

Your client has been given the following description of your work and capabilities: 

{description}

## Parameters

Your client has provided the following parameters for your task:

{parameters}
""".strip()


@dataclass
class Parameter:
    """Agent parameter with name, description and value."""
    name: str
    description: str
    value: str


@dataclass
class AgentOutput:
    """Agent output containing result, summary and feedback."""
    result: str
    summary: str
    feedback: str | None = None


@dataclass
class Agent:
    """Agent data structure with immutable configuration and mutable state."""
    
    # Immutable configuration
    name: str
    model: str
    description: str
    parameters: List[Parameter]
    feedback_function: Callable
    
    # Mutable state
    history: list = field(default_factory=list)
    shortened_conversation: str | None = None
    output: AgentOutput | None = None
    
    def create_start_message(self) -> str:
        """Create the initial message for the agent."""
        parameters_str = self._format_parameters()
        return START_MESSAGE_TEMPLATE.format(
            name=self.name,
            description=textwrap.indent(self.description, "  "),
            parameters=textwrap.indent(parameters_str, "  "),
        )
    
    def _format_parameters(self) -> str:
        """Format parameters for display."""
        parameter_descriptions = []
        
        for parameter in self.parameters:
            value_str = parameter.value
            
            if "\n" in value_str:
                value_str = "\n" + textwrap.indent(value_str, "  ")
            
            parameter_descriptions.append(
                PARAMETER_TEMPLATE.format(
                    name=parameter.name,
                    description=parameter.description,
                    value=value_str,
                )
            )
        
        return "\n\n".join(parameter_descriptions)
    
    def reset_output(self):
        """Reset agent output (for feedback loops)."""
        self.output = None
    
    def set_output(self, result: str, summary: str, feedback: str | None = None):
        """Set agent output."""
        self.output = AgentOutput(result=result, summary=summary, feedback=feedback)
    
    def set_shortened_conversation(self, summary: str):
        """Set conversation summary for history truncation."""
        self.shortened_conversation = summary
    
    def clear_history(self):
        """Clear conversation history."""
        self.history = []
    
    def to_dict(self) -> dict:
        """Convert agent to dictionary for serialization."""
        return {
            "name": self.name,
            "model": self.model,
            "description": self.description,
            "parameters": [dataclasses.asdict(p) for p in self.parameters],
            "history": self.history,
            "shortened_conversation": self.shortened_conversation,
            "output": dataclasses.asdict(self.output) if self.output else None,
        }


def fill_parameters(parameter_description: dict, parameter_values: dict) -> List[Parameter]:
    """Fill parameter objects from schema and values."""
    parameters = []
    required = set(parameter_description.get("required", []))
    
    for name, parameter in parameter_description["properties"].items():
        # Check if required parameters are provided
        if name not in parameter_values or parameter_values[name] is None:
            if name in required:
                raise RuntimeError(f"Parameter {name} is required but not provided.")
            else:
                continue
        
        # Convert parameter values to string representations
        parameter_type = parameter.get("type")
        if parameter_type == "string":
            if not isinstance(parameter_values[name], str):
                raise RuntimeError(f"Parameter {name} is not a string: {parameter_values[name]}")
            value = parameter_values[name]
        elif parameter_type == "array":
            if not isinstance(parameter_values[name], list):
                raise RuntimeError(f"Parameter {name} is not an array: {parameter_values[name]}")
            value = textwrap.indent("\n".join(parameter_values[name]), "- ")
        elif parameter_type == "boolean":
            if not isinstance(parameter_values[name], bool):
                raise RuntimeError(f"Parameter {name} is not a boolean: {parameter_values[name]}")
            value = str(parameter_values[name])
        else:
            raise RuntimeError(f"Unsupported parameter type: {parameter_type} for parameter {name}")
        
        parameters.append(
            Parameter(
                name=name,
                description=parameter["description"],
                value=value,
            )
        )
    
    return parameters


def format_parameters(parameters: List[Parameter]) -> str:
    """Format parameters for display."""
    parameter_descriptions = []
    
    for parameter in parameters:
        value_str = parameter.value
        
        if "\n" in value_str:
            value_str = "\n" + textwrap.indent(value_str, "  ")
        
        parameter_descriptions.append(
            PARAMETER_TEMPLATE.format(
                name=parameter.name,
                description=parameter.description,
                value=value_str,
            )
        )
    
    return "\n\n".join(parameter_descriptions)

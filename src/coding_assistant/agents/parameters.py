import textwrap
from dataclasses import dataclass


@dataclass
class Parameter:
    name: str
    description: str
    value: str


def fill_parameters(
    parameter_description: dict,
    parameter_values: dict,
) -> list[Parameter]:
    parameters = []
    required = set(parameter_description.get("required", []))

    for name, schema in parameter_description["properties"].items():
        # Skip missing optional parameters
        if name not in parameter_values or parameter_values[name] is None:
            if name in required:
                raise RuntimeError(f"Required parameter '{name}' is missing")
            continue

        # Determine parameter type from schema
        param_type = _extract_type_from_schema(schema)
        if not param_type:
            raise RuntimeError(f"Could not determine type for parameter '{name}': {schema}")

        # Convert value to string representation
        value = _format_value_by_type(parameter_values[name], name)

        parameters.append(
            Parameter(
                name=name,
                description=schema.get("description", ""),
                value=value,
            )
        )

    return parameters


def _extract_type_from_schema(schema: dict) -> str | None:
    """Extract the parameter type from a JSON schema."""
    if "type" in schema:
        return schema["type"]

    if "anyOf" in schema:
        # Find the first non-null type in anyOf
        for type_option in schema["anyOf"]:
            if type_option.get("type") not in (None, "null"):
                return type_option.get("type")

    return None


def _format_value_by_type(value, param_name: str) -> str:
    """Format a parameter value according to its type."""
    if isinstance(value, str):
        return value
    elif isinstance(value, list):
        formatted_items = []
        for item in value:
            item_str = str(item)
            if item_str.startswith("- "):
                formatted_items.append(item_str)
            else:
                formatted_items.append(f"- {item_str}")
        return "\n".join(formatted_items)
    elif isinstance(value, bool):
        return str(value)
    elif isinstance(value, (int, float)):
        return str(value)
    else:
        raise RuntimeError(f"Unsupported parameter type for parameter '{param_name}'")


def format_parameters(parameters: list[Parameter]) -> str:
    PARAMETER_TEMPLATE = """
- Name: {name}
  - Description: {description}
  - Value: {value}
""".strip()
    parameter_descriptions = []

    for parameter in parameters:
        value_str = parameter.value

        if "\n" in value_str:
            value_str = "\n" + textwrap.indent(value_str, "    ")

        parameter_descriptions.append(
            PARAMETER_TEMPLATE.format(
                name=parameter.name,
                description=parameter.description,
                value=value_str,
            )
        )

    return "\n\n".join(parameter_descriptions)

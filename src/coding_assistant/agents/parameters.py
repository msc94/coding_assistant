from dataclasses import dataclass
import textwrap

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

    for name, parameter in parameter_description["properties"].items():
        # Check if required parameters are provided
        if name not in parameter_values or parameter_values[name] is None:
            if name in required:
                raise RuntimeError(f"Parameter {name} is required but not provided.")
            else:
                continue

        # Convert all parameter values to sensible string representations
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


def format_parameters(parameters: list[Parameter]) -> str:
    PARAMETER_TEMPLATE = """
Name: {name}
Description: {description}
Value: {value}
""".strip()
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

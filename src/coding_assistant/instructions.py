from __future__ import annotations

import logging
from pathlib import Path

from coding_assistant.tools.mcp import MCPServer

logger = logging.getLogger(__name__)


def _load_default_instructions() -> str:
    default_instructions_path = Path(__file__).parent / "default_instructions.md"
    if not default_instructions_path.exists():
        raise FileNotFoundError("Could not find default_instructions.md")
    return default_instructions_path.read_text().strip()


def get_instructions(
    working_directory: Path,
    user_instructions: list[str],
    mcp_servers: list[MCPServer] | None = None,
) -> str:
    sections: list[str] = []

    sections.append(_load_default_instructions())

    for path in [
        working_directory / ".coding_assistant" / "instructions.md",
        working_directory / "AGENTS.md",
    ]:
        if not path.exists():
            continue

        content = path.read_text().strip()
        if not content:
            continue

        sections.append(content)

    for server in mcp_servers or []:
        text = getattr(server, "instructions", None)
        if text and text.strip():
            sections.append(f"# MCP `{server.name}` instructions\n\n{text.strip()}")

    if user_instructions:
        sections.append("# User-provided instructions")
        for user_instruction in user_instructions:
            if user_instruction and user_instruction.strip():
                sections.append(user_instruction.strip())

    for section in sections:
        if not section.startswith("# "):
            logger.warning(f"Instruction section {section} does not start with a top-level heading")

    return "\n\n".join(sections)

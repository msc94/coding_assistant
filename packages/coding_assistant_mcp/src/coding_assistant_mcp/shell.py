from __future__ import annotations

import asyncio
import re
from typing import Annotated

from prompt_toolkit import prompt as ptk_prompt
from prompt_toolkit.styles import Style

from fastmcp import FastMCP

shell_server = FastMCP()

# Patterns configured at runtime via CLI args in main.py
_SHELL_CONFIRMATION_PATTERNS: list[str] = []



def set_shell_confirmation_patterns(patterns: list[str]) -> None:
    """Configure the regex patterns which require explicit confirmation.

    When a command matches one of these patterns, the caller must supply
    confirm=True to actually execute it. Otherwise a descriptive message is
    returned and the command is NOT executed.
    """

    global _SHELL_CONFIRMATION_PATTERNS
    _SHELL_CONFIRMATION_PATTERNS = patterns


async def execute(
    command: Annotated[str, "The shell command to execute. Do not include 'bash -c'."],
    timeout: Annotated[int, "The timeout for the command in seconds."] = 30,
    truncate_at: Annotated[int, "Maximum number of characters to return in stdout/stderr combined."] = 50_000,
) -> str:
    """Execute a shell command using bash and return combined stdout/stderr.

    If the command matches any configured confirmation pattern, the user is
    prompted (using prompt_toolkit) to confirm execution (y/yes to proceed).
    """
    command = command.strip()

    matched_pattern: str | None = None
    for pattern in _SHELL_CONFIRMATION_PATTERNS:
        if re.search(pattern, command):
            matched_pattern = pattern
            break

    if matched_pattern:
        confirmed = await asyncio.to_thread(_ask_confirmation, command)
        if not confirmed:
            return "Command execution denied."

    try:
        proc = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        return f"Command timed out after {timeout} seconds."

    if proc.returncode != 0:
        result = f"Returncode: {proc.returncode}\n\n{stdout.decode()}"
    else:
        result = stdout.decode()

    if len(result) > truncate_at:
        note = "\n\n[truncated output due to truncate_at limit]"
        truncated = result[: max(0, truncate_at - len(note))]
        result = truncated + note

    return result

shell_server.tool(execute)


# --- internal helpers ---
_STYLE = Style.from_dict(
    {
        "prompt": "ansibrightblack",
        "command": "ansiyellow",
    }
)


def _ask_confirmation(command: str) -> bool:
    """Prompt the user for confirmation using prompt_toolkit (falls back to input)."""
    msg = f"Execute `{command}`? (y/N): "
    try:
        answer = ptk_prompt(msg, style=_STYLE)
    except Exception:
        # Fallback to plain input if prompt_toolkit rendering fails (e.g., non-interactive TTY)
        answer = input(msg)
    return answer.strip().lower() in ("y", "yes")

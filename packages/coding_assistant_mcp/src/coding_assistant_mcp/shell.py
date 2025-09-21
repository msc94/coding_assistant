from __future__ import annotations

import asyncio
import re
import uuid
from typing import Annotated, Dict, Tuple

from fastmcp import FastMCP

shell_server = FastMCP()

# Patterns configured at runtime via CLI args in main.py
_SHELL_CONFIRMATION_PATTERNS: list[str] = []

# token -> (command, timeout, truncate_at)
_PENDING_CONFIRMATIONS: Dict[str, Tuple[str, int, int]] = {}


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

    Confirmation semantics:
    - If the command matches a configured confirmation pattern, execution is deferred.
      A token is returned: the caller must obtain explicit user confirmation (e.g. via a
      separate prompt mechanism) and then invoke shell_confirm with that token.
    - If no pattern matches, the command executes immediately.
    """
    command = command.strip()

    matched_pattern: str | None = None
    for pattern in _SHELL_CONFIRMATION_PATTERNS:
        if re.search(pattern, command):
            matched_pattern = pattern
            break

    if matched_pattern:
        token = uuid.uuid4().hex
        _PENDING_CONFIRMATIONS[token] = (command, timeout, truncate_at)
        return (
            f"CONFIRMATION REQUIRED: Command matches pattern '{matched_pattern}'.\n"
            f"Token: {token}\n"
            "Call shell_confirm with this token after user approval to execute.\n"
            f"Command: `{command}`"
        )

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


async def confirm(
    token: Annotated[str, "The confirmation token previously returned by shell_execute."],
) -> str:
    """Confirm and execute a previously requested command.

    If the token is unknown or already used, a message is returned.
    """
    info = _PENDING_CONFIRMATIONS.pop(token, None)
    if not info:
        return "Invalid or already used confirmation token."

    command, timeout, truncate_at = info

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


shell_server.tool(confirm)

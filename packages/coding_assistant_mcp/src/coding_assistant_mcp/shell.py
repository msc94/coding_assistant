from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional, Annotated

from fastmcp import FastMCP


@dataclass
class ExecuteInput:
    command: Annotated[str, "The shell command to execute."]
    timeout: Annotated[Optional[int], "The timeout for the command in seconds."] = None
    truncate_at: Annotated[
        Optional[int], "Max chars for combined stdout/stderr; truncates with a note when exceeded."
    ] = None



shell_server = FastMCP()


async def execute(
    command: Annotated[str, "The shell command to execute."],
    timeout: Annotated[Optional[int], "The timeout for the command in seconds."] = None,
    truncate_at: Annotated[Optional[int], "Maximum number of characters to return in stdout/stderr combined."] = None,
) -> str:
    """Execute a shell command using `bash -c` and return combined stdout/stderr.

    Behavior:
    - Uses a default timeout of 30s if `timeout` is None.
    - Uses a default truncation limit of 50,000 characters if `truncate_at` is None.
    - If the process exits with non‑zero status, the return code is prepended.
    - Output longer than the limit is truncated with a note.
    - On timeout, returns a timeout message (no partial output).

    Provide only the command; do NOT include 'bash -c'.
    """
    command = command.strip()
    effective_timeout = 30 if timeout is None else timeout
    effective_truncate_at = 50_000 if truncate_at is None else truncate_at

    try:
        proc = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=effective_timeout)
    except asyncio.TimeoutError:
        return f"Command timed out after {effective_timeout} seconds."

    if proc.returncode != 0:
        result = f"Returncode: {proc.returncode}\n\n{stdout.decode()}"
    else:
        result = stdout.decode()

    if len(result) > effective_truncate_at:
        note = "\n\n[truncated output due to truncate_at limit]"
        truncated = result[: max(0, effective_truncate_at - len(note))]
        result = truncated + note

    return result


# Register function with FastMCP server so it's exposed, while keeping it directly callable for tests
shell_server.tool(execute)

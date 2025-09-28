import os
from pathlib import Path

import pytest

from typing import cast

from coding_assistant.instructions import get_instructions
from coding_assistant.tools.mcp import MCPServer


def test_get_instructions_base_and_user_instructions(tmp_path: Path):
    wd = tmp_path
    # No local file, no planning
    instr = get_instructions(working_directory=wd, plan=False, user_instructions=["  A  ", "B\n"])

    # Key baseline rules should be present
    assert "Do not initialize a new git repository" in instr
    # User instructions appended, trimmed and in order
    assert "\nA\n" in instr
    # Second item may be at end without trailing newline
    assert "\nB\n" in instr or instr.rstrip().endswith("\nB") or instr.endswith("B")


def test_get_instructions_with_planning_and_local_file(tmp_path: Path):
    wd = tmp_path
    local_dir = wd / ".coding_assistant"
    local_dir.mkdir()
    (local_dir / "instructions.md").write_text("LOCAL OVERRIDE\n- extra rule")

    instr = get_instructions(working_directory=wd, plan=True, user_instructions=[])

    # Planning block should be included
    assert "You are in planning mode." in instr
    # Local instructions appended
    assert "LOCAL OVERRIDE" in instr
    assert "- extra rule" in instr


def test_get_instructions_appends_mcp_instructions(tmp_path: Path):
    wd = tmp_path

    class _FakeServer:
        def __init__(self, instructions: str | None):
            self.instructions = instructions

    s1 = _FakeServer("- Use server1 tools whenever possible.")
    s2 = _FakeServer("- Server2: prefer safe operations.")

    instr = get_instructions(
        working_directory=wd,
        plan=False,
        user_instructions=[],
        mcp_servers=cast(list[MCPServer], [s1, s2]),
    )

    assert "Use server1 tools whenever possible." in instr
    assert "Server2: prefer safe operations." in instr


def test_get_instructions_ignores_empty_or_missing_mcp_instructions(tmp_path: Path):
    wd = tmp_path

    class _NoAttrServer:
        pass

    class _BlankServer:
        def __init__(self, instructions: str | None):
            self.instructions = instructions

    s1 = _BlankServer("   ")  # only whitespace
    s2 = _BlankServer("")  # empty
    s3 = _BlankServer(None)  # None
    s4 = _NoAttrServer()  # no instructions attribute

    instr = get_instructions(
        working_directory=wd,
        plan=False,
        user_instructions=[],
        mcp_servers=cast(list[MCPServer], [s1, s2, s3, s4]),
    )

    # Ensure baseline rule present and nothing from the servers leaked
    assert "Do not initialize a new git repository" in instr
    assert "Server" not in instr

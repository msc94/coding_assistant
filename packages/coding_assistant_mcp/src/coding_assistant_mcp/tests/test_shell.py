import pytest

from coding_assistant_mcp.shell import execute


@pytest.mark.asyncio
async def test_shell_execute_timeout():
    out = await execute(command="sleep 2", timeout=1)
    assert "timed out" in out


@pytest.mark.asyncio
async def test_shell_execute_nonzero_return_code():
    out = await execute(command="bash -lc 'exit 7'")
    assert out.startswith("Returncode: 7\n\n")


@pytest.mark.asyncio
async def test_shell_execute_truncates_output():
    out = await execute(command="yes 1 | head -c 1000", truncate_at=200)
    assert out.endswith("\n\n[truncated output due to truncate_at limit]")
    assert len(out) <= 200

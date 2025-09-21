import pytest
from coding_assistant_mcp.todo import create_todo_server, TodoManager


@pytest.fixture()
def todo_server():
    # Fresh server (and underlying manager) per test
    server = create_todo_server()
    return server

def _call(server, name: str, **kwargs):
    tools = getattr(server, "_todo_tools")  # type: ignore[attr-defined]
    return tools[name](**kwargs)


def test_add_and_list_single(todo_server):
    r1 = _call(todo_server, "add", descriptions=["Write tests"])  # type: ignore
    assert r1.strip() == "- [ ] 1: Write tests"
    r2 = _call(todo_server, "add", descriptions=["Refactor code"])  # type: ignore
    # After second add, output is the full list with both tasks
    lines = r2.splitlines()
    assert "- [ ] 1: Write tests" in lines
    assert any(l.endswith("2: Refactor code") for l in lines)

    text = _call(todo_server, "list_todos")  # type: ignore
    assert "1: Write tests" in text
    assert "2: Refactor code" in text


def test_complete(todo_server):
    _call(todo_server, "add", descriptions=["Implement feature"])  # type: ignore
    _call(todo_server, "add", descriptions=["Write docs"])  # type: ignore
    complete_res = _call(todo_server, "complete", task_id=1)  # type: ignore
    assert complete_res.startswith("Completed TODO 1: Implement feature\n")
    assert "- [x] 1: Implement feature" in complete_res
    assert "- [ ] 2: Write docs" in complete_res
    # After completion, listing should show the completed task with an x (independently via list_todos)
    text = _call(todo_server, "list_todos")  # type: ignore
    assert "- [x] 1: Implement feature" in text
    assert "- [ ] 2: Write docs" in text


def test_complete_with_result(todo_server):
    _call(todo_server, "add", descriptions=["Run benchmarks"])  # type: ignore
    _call(todo_server, "add", descriptions=["Prepare release notes"])  # type: ignore
    res = _call(todo_server, "complete", task_id=1, result="Throughput +12% vs baseline")  # type: ignore

    lines = res.splitlines()
    # Output should include completion message with result inline
    assert lines[0] == "Completed TODO 1: Run benchmarks with result: Throughput +12% vs baseline"
    # Listing shows the result inline with an arrow now
    listing = _call(todo_server, "list_todos")  # type: ignore
    # Result is now rendered on a separate indented line after the task
    assert "- [x] 1: Run benchmarks\n -> Throughput +12% vs baseline" in listing
    assert "- [ ] 2: Prepare release notes" in listing


def test_complete_invalid(todo_server):
    # No tasks yet
    res = _call(todo_server, "complete", task_id=1)  # type: ignore
    assert res.startswith("TODO 1 not found\n")
    _call(todo_server, "add", descriptions=["Something"])  # type: ignore
    res2 = _call(todo_server, "complete", task_id=99)  # type: ignore
    assert res2.startswith("TODO 99 not found\n")


def test_add_multiple_and_invalid(todo_server):
    out = _call(todo_server, "add", descriptions=["A", "B"])  # type: ignore
    lines = out.splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("1: A")
    assert lines[1].endswith("2: B")

    # Empty description should raise
    with pytest.raises(ValueError):
        _call(todo_server, "add", descriptions=[""])  # type: ignore


def test_complete_ignores_empty_result(todo_server):
    _call(todo_server, "add", descriptions=["Do something"])  # type: ignore
    res = _call(todo_server, "complete", task_id=1, result="")  # type: ignore  # empty result should be ignored
    # Completion line should not show 'with result:' when empty
    first_line = res.splitlines()[0]
    assert first_line == "Completed TODO 1: Do something"
    listing = _call(todo_server, "list_todos")  # type: ignore
    # List line should not have arrow because result ignored
    assert "- [x] 1: Do something ->" not in listing
    assert "- [x] 1: Do something" in listing

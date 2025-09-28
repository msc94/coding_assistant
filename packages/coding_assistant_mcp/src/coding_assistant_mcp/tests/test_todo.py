import pytest
from coding_assistant_mcp.todo import TodoManager


@pytest.fixture()
def manager():
    return TodoManager()


def test_add_and_list_single(manager: TodoManager):
    r1 = manager.add(["Write tests"])  # type: ignore[arg-type]
    assert r1.strip() == "- [ ] 1: Write tests"
    r2 = manager.add(["Refactor code"])  # type: ignore[arg-type]
    # After second add, output is the full list with both tasks
    lines = r2.splitlines()
    assert "- [ ] 1: Write tests" in lines
    assert any(line.endswith("2: Refactor code") for line in lines)

    text = manager.list_todos()
    assert "1: Write tests" in text
    assert "2: Refactor code" in text


def test_complete(manager: TodoManager):
    manager.add(["Implement feature"])  # type: ignore[arg-type]
    manager.add(["Write docs"])  # type: ignore[arg-type]
    complete_res = manager.complete(1)
    assert complete_res.startswith("Completed TODO 1: Implement feature\n")
    assert "- [x] 1: Implement feature" in complete_res
    assert "- [ ] 2: Write docs" in complete_res
    # After completion, listing should show the completed task with an x (independently via list_todos)
    text = manager.list_todos()
    assert "- [x] 1: Implement feature" in text
    assert "- [ ] 2: Write docs" in text


def test_complete_with_result(manager: TodoManager):
    manager.add(["Run benchmarks"])  # type: ignore[arg-type]
    manager.add(["Prepare release notes"])  # type: ignore[arg-type]
    res = manager.complete(1, result="Throughput +12% vs baseline")

    lines = res.splitlines()
    # Output should include completion message with result inline
    assert lines[0] == "Completed TODO 1: Run benchmarks with result: Throughput +12% vs baseline"
    # Listing shows the result inline with an arrow (single line)
    listing = manager.list_todos()
    assert "- [x] 1: Run benchmarks -> Throughput +12% vs baseline" in listing
    assert "- [ ] 2: Prepare release notes" in listing


def test_complete_invalid(manager: TodoManager):
    # No tasks yet
    res = manager.complete(1)
    assert res.startswith("TODO 1 not found\n")
    manager.add(["Something"])  # type: ignore[arg-type]
    res2 = manager.complete(99)
    assert res2.startswith("TODO 99 not found\n")


def test_add_multiple_and_invalid(manager: TodoManager):
    out = manager.add(["A", "B"])  # type: ignore[arg-type]
    lines = out.splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("1: A")
    assert lines[1].endswith("2: B")

    # Empty description should raise
    with pytest.raises(ValueError):
        manager.add([""])  # type: ignore[arg-type]


def test_complete_ignores_empty_result(manager: TodoManager):
    manager.add(["Do something"])  # type: ignore[arg-type]
    res = manager.complete(1, result="")  # empty result should be ignored
    # Completion line should not show 'with result:' when empty
    first_line = res.splitlines()[0]
    assert first_line == "Completed TODO 1: Do something"
    listing = manager.list_todos()
    # List line should not have arrow because result ignored
    assert "- [x] 1: Do something ->" not in listing
    assert "- [x] 1: Do something" in listing

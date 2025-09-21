from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Annotated

from fastmcp import FastMCP


@dataclass
class Todo:
    id: int
    description: str
    completed: bool = False
    result: Optional[str] = None


class TodoManager:
    def __init__(self) -> None:
        self._todos: dict[int, Todo] = dict()
        self._next_id = 1

    def add(self, description: str) -> Todo:
        todo = Todo(id=self._next_id, description=description)
        self._todos[todo.id] = todo
        self._next_id += 1
        return todo

    def complete(self, task_id: int, result: str | None = None) -> Todo | None:
        todo = self._todos.get(task_id)
        if todo:
            todo.completed = True
            if result is not None:
                todo.result = result
            return todo
        return None

    def format(self) -> str:
        lines: list[str] = []
        for t in self._todos.values():
            box = "x" if t.completed else " "

            if t.result:
                lines.append(f"- [{box}] {t.id}: {t.description} -> {t.result}")
            else:
                lines.append(f"- [{box}] {t.id}: {t.description}")

        return "\n".join(lines)


_MANAGER: Optional[TodoManager] = None


def get_manager() -> TodoManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = TodoManager()
    return _MANAGER


def reset_state() -> None:
    global _MANAGER
    _MANAGER = None


def add(descriptions: Annotated[list[str], "List of non-empty TODO description strings"]) -> str:
    """Add TODO items.

    Args:
        descriptions: A list of non-empty description strings. Empty strings raise ``ValueError``.

    Returns:
        A markdown rendering of the full TODO list after insertion.

    Raises:
        ValueError: If any provided description is empty.
    """

    manager = get_manager()
    for desc in descriptions:
        if not desc:
            raise ValueError("Description must not be empty.")
        manager.add(desc)
    return manager.format()


def list_todos() -> str:
    """List all TODO items.

    Returns:
        A markdown task list representation of every TODO (completed and pending).
    """
    return get_manager().format()


def complete(
    task_id: Annotated[int, "ID of the TODO to mark complete"],
    result: Annotated[str | None, "Optional result text (one line) to attach"] = None,
) -> str:
    """Complete a TODO item and return an updated list.

    Args:
        task_id: ID of the TODO to mark complete.
        result: Optional short (one line) descriptive outcome / result text to associate. None can be passed to indicate no result.

    Returns:
        Markdown output consisting of a completion message followed by the full
        rendered list.
    """
    manager = get_manager()

    output = ""
    if todo := manager.complete(task_id, result=result):
        output += f"Completed TODO {task_id}: {todo.description}"
        if result:
            output += f" with result: {result}\n"
        else:
            output += "\n"
    else:
        output += f"TODO {task_id} not found\n"

    output += "\n"
    output += manager.format()

    return output


todo_server = FastMCP()
todo_server.tool(complete)
todo_server.tool(list_todos)
todo_server.tool(add)
# todo_server.tool(reset_state)

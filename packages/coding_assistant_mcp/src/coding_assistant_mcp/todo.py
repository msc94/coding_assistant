from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Annotated

from fastmcp import FastMCP


@dataclass
class Todo:
    """A single TODO item.

    Attributes:
        id: Autoincrementing integer identifier assigned by the manager.
        description: Short human readable description of the task.
        completed: Whether the task has been marked complete.
        result: Optional result / output text captured when the task is completed.
    """

    id: int
    description: str
    completed: bool = False
    result: Optional[str] = None


class TodoManager:
    """In‑memory manager for TODO items.

    This class is intentionally minimal; it performs no persistence and is safe for
    single‑process use only. IDs are allocated sequentially starting from 1.
    """

    def __init__(self) -> None:
        """Initialize an empty manager."""
        self._todos: dict[int, Todo] = dict()
        self._next_id = 1

    def add(self, description: str) -> Todo:
        """Create and store a new TODO item.

        Args:
            description: Non‑empty task description.

        Returns:
            The newly created ``Todo`` instance.
        """
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
    """Get the process‑global ``TodoManager`` instance, creating it if needed.

    Returns:
        The singleton ``TodoManager``.
    """
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = TodoManager()
    return _MANAGER


def reset_state() -> None:
    global _MANAGER
    _MANAGER = None


def add(descriptions: Annotated[list[str], "List of non-empty TODO description strings"]) -> str:
    """Add one or more TODO items and return the updated list.

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
    """Return all TODO items as a markdown task list."""
    return get_manager().format()


def complete(
    task_id: Annotated[int, "ID of the TODO to mark complete"],
    result: Annotated[str | None, "Optional result text (one line) to attach"] = None,
) -> str:
    """Mark a task complete and return a completion message plus the full list."""
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

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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

    def complete(self, task_id: int, result: Optional[str] = None) -> Todo | None:
        """Mark the specified TODO as completed.

        Args:
            task_id: Identifier of the TODO to complete.
            result: Optional non‑empty result string to attach when completing.

        Returns:
            The updated ``Todo`` if it existed; otherwise ``None``.
        """
        todo = self._todos.get(task_id)
        if todo:
            todo.completed = True
            if result is not None and result != "":
                todo.result = result
            return todo
        return None

    def format(self) -> str:
        """Render the current TODO list as a markdown task list.

        Returns:
            A markdown string. Completed tasks are marked with ``[x]`` and, when
            present, result text appears on an indented line below the task.
        """
        lines: list[str] = []
        for t in self._todos.values():
            box = "x" if t.completed else " "
            lines.append(f"- [{box}] {t.id}: {t.description}")
            if t.result:
                lines.append(f"  Result: {t.result}")
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
    """Reset global TODO state.

    Clears the singleton manager so subsequent calls to ``get_manager`` create a
    fresh instance. Primarily intended for tests.
    """
    global _MANAGER
    _MANAGER = None


def add(descriptions: list[str]) -> str:
    """Add one or more TODO items.

    Args:
        descriptions: A list of non‑empty description strings. Empty strings
            raise ``ValueError``.

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


def complete(task_id: int, result: Optional[str] = None) -> str:
    """Complete a TODO item and return an updated list.

    Args:
        task_id: ID of the TODO to mark complete.
        result: Optional descriptive outcome / result text to associate. Empty
            strings are ignored.

    Returns:
        Markdown output consisting of a completion message followed by the full
        rendered list.
    """
    manager = get_manager()

    output = ""
    if todo := manager.complete(task_id, result=result):
        output += f"Completed TODO {task_id}: {todo.description}\n"
        if result:
            output += f"Result: {result}\n"
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

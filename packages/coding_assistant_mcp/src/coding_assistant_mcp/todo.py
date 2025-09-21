from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional

from fastmcp import FastMCP


@dataclass
class Todo:
    id: int
    description: str
    completed: bool = False
    result: Optional[str] = None


class TodoManager:
    """In-memory TODO manager.

    This object is intentionally simple; callers create a new instance per
    server so no global state is shared across servers / tests.
    """

    def __init__(self) -> None:
        self._todos: dict[int, Todo] = {}
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

    def reset(self) -> None:
        self._todos.clear()
        self._next_id = 1

    def format(self) -> str:
        lines: list[str] = []
        for t in self._todos.values():
            box = "x" if t.completed else " "
            if t.result:
                lines.append(f"- [{box}] {t.id}: {t.description}\n -> {t.result}")
            else:
                lines.append(f"- [{box}] {t.id}: {t.description}")
        return "\n".join(lines)


def create_todo_server() -> FastMCP:
    """Create a fresh FastMCP server exposing TODO tools without global state.

    Each invocation returns a new server instance with an isolated in-memory
    store so test runs or multiple parent processes do not interfere.
    """

    manager = TodoManager()
    server = FastMCP()

    # Tool functions capture the manager via closure – no globals needed.
    def add(
        descriptions: Annotated[list[str], "List of non-empty TODO description strings"],
    ) -> str:
        """Add one or more TODO items and return the updated list.

        Raises:
            ValueError: If any provided description is empty.
        """
        for desc in descriptions:
            if not desc:
                raise ValueError("Description must not be empty.")
            manager.add(desc)
        return manager.format()

    def list_todos() -> str:
        """Return all TODO items as a markdown task list."""
        return manager.format()

    def complete(
        task_id: Annotated[int, "ID of the TODO to mark complete"],
        result: Annotated[str | None, "Optional result text (one line) to attach"] = None,
    ) -> str:
        """Mark a task complete and return a completion message plus the full list."""
        output = ""
        if todo := manager.complete(task_id, result=result):
            output += f"Completed TODO {task_id}: {todo.description}"
            if result:
                output += f" with result: {result}\n"
            else:
                output += "\n"
        else:
            output += f"TODO {task_id} not found\n"
        output += "\n" + manager.format()
        return output

    def reset() -> str:
        """Reset the in-memory TODO list."""
        manager.reset()
        return "Reset TODO list (now empty)."

    # Register tools
    server.tool(add)
    server.tool(list_todos)
    server.tool(complete)
    server.tool(reset)

    # Provide an accessor to the manager for optional advanced uses / tests.
    setattr(server, "_todo_manager", manager)  # type: ignore[attr-defined]
    # Expose raw functions for direct invocation in unit tests (not part of public API)
    setattr(
        server,
        "_todo_tools",
        {
            "add": add,
            "list_todos": list_todos,
            "complete": complete,
            "reset": reset,
        },
    )  # type: ignore[attr-defined]

    return server

__all__ = [
    "Todo",
    "TodoManager",
    "create_todo_server",
]

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
    """In-memory TODO manager with tool methods registered onto FastMCP.

    Tool-facing methods (add, list_todos, complete, reset) return strings for
    LLM consumption. Internal helpers (add_item, complete_item) return domain
    objects.
    """

    def __init__(self) -> None:
        self._todos: dict[int, Todo] = {}
        self._next_id = 1

    # --- Internal helpers -------------------------------------------------
    def add_item(self, description: str) -> Todo:
        todo = Todo(id=self._next_id, description=description)
        self._todos[todo.id] = todo
        self._next_id += 1
        return todo

    def complete_item(self, task_id: int, result: str | None = None) -> Todo | None:
        todo = self._todos.get(task_id)
        if todo:
            todo.completed = True
            if result is not None and result != "":
                todo.result = result
            return todo
        return None

    def reset_items(self) -> None:
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

    # --- Tool methods -----------------------------------------------------
    def add(
        self,
        descriptions: Annotated[list[str], "List of non-empty TODO description strings"],
    ) -> str:
        """Add one or more TODO items and return the updated list.

        Raises:
            ValueError: If any provided description is empty.
        """
        for desc in descriptions:
            if not desc:
                raise ValueError("Description must not be empty.")
            self.add_item(desc)
        return self.format()

    def list_todos(self) -> str:  # noqa: D401 - concise
        """Return all TODO items as a markdown task list."""
        return self.format()

    def complete(
        self,
        task_id: Annotated[int, "ID of the TODO to mark complete"],
        result: Annotated[str | None, "Optional result text (one line) to attach"] = None,
    ) -> str:
        """Mark a task complete and return a completion message plus the full list."""
        output = ""
        if todo := self.complete_item(task_id, result=result):
            output += f"Completed TODO {task_id}: {todo.description}"
            if result:
                output += f" with result: {result}\n"
            else:
                output += "\n"
        else:
            output += f"TODO {task_id} not found\n"
        output += "\n" + self.format()
        return output

    def reset(self) -> str:
        """Reset the in-memory TODO list."""
        self.reset_items()
        return "Reset TODO list (now empty)."


def create_todo_server() -> FastMCP:
    """Create a fresh FastMCP server exposing TODO tools without global state.

    Each invocation returns a new server instance with an isolated in-memory
    store so test runs or multiple parent processes do not interfere.
    """

    manager = TodoManager()
    server = FastMCP()

    # Register bound methods directly; FastMCP will see signatures without 'self'.
    for method_name in ["add", "list_todos", "complete", "reset"]:
        server.tool(getattr(manager, method_name))

    return server

__all__ = [
    "Todo",
    "TodoManager",
    "create_todo_server",
]

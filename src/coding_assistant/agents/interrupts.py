import signal
from asyncio import AbstractEventLoop, Task
from types import FrameType
from typing import Any, Callable


class InterruptController:
    """Coordinates user interrupts, signal handling, and tool-task cancellation."""

    def __init__(self, loop: AbstractEventLoop) -> None:
        self._loop = loop
        self._tasks: set[Task[Any]] = set()
        self._original_handler: Callable[[int, FrameType | None], Any] | int | None = None

    def _signal_handler(self, signum: int, frame: FrameType | None) -> None:
        """Handle SIGINT signals."""
        self._loop.call_soon_threadsafe(self._cancel_all_tasks)

    def __enter__(self) -> "InterruptController":
        """Set up SIGINT handler."""
        self._original_handler = signal.signal(signal.SIGINT, self._signal_handler)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Restore original SIGINT handler."""
        if self._original_handler is not None:
            signal.signal(signal.SIGINT, self._original_handler)

    def register_task(self, call_id: str, task: Task[Any]) -> None:
        self._tasks.add(task)
        task.add_done_callback(lambda finished_task: self._tasks.discard(finished_task))

    def _cancel_all_tasks(self) -> None:
        for task in list(self._tasks):
            task.cancel()

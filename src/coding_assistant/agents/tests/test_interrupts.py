import asyncio
import os
import signal

import pytest

from coding_assistant.agents.interrupts import InterruptController


@pytest.mark.asyncio
async def test_interrupt_controller_cancels_tasks_on_sigint():
    """Test that SIGINT cancels registered tasks."""
    loop = asyncio.get_running_loop()

    async def wait_forever():
        await asyncio.Future()

    with InterruptController(loop) as controller:
        task = loop.create_task(wait_forever())
        controller.register_task("call-1", task)

        os.kill(os.getpid(), signal.SIGINT)
        await asyncio.sleep(0)

        with pytest.raises(asyncio.CancelledError):
            await task

        assert task.cancelled()
        # Task should be removed from the set after completion
        assert len(controller._tasks) == 0

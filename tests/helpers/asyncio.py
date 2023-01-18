import aiofiles
import asyncio
import threading
from typing import Optional


def task_from_blocking(blocking_func):
    return asyncio.create_task(
        asyncio.to_thread(blocking_func),
    )


def wait_ev(
    ev: threading.Event,
    on_done=lambda: None,
    event_id: str = "",
):
    def _inner():
        ev.wait()
        on_done()
        # ev.clear()

    return _inner


async def wait_ev_async(
    ev: threading.Event,
    timeout: Optional[float] = None,
):
    return await asyncio.wait_for(
        task_from_blocking(wait_ev(ev)),
        timeout=timeout,
    )


async def read_bytes(path: str):
    async with aiofiles.open(path, "rb") as f:
        return await f.read()

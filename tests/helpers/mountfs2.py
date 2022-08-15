import asyncio
import multiprocessing
import os
import threading
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

import pyfuse3
import pyfuse3_asyncio
from tgmount import fs

from ..helpers.mount import wait_for_mount, cleanup, umount


@dataclass
class MountContext:
    tmpdir: str
    exit_event: Optional[threading.Event] = None
    events: list[threading.Event] = field(default_factory=list)

    def path(self, *p: str):
        return os.path.join(self.tmpdir, *p)


OnEventCallback = Callable[[], Awaitable[None]]
OnEventSetCallback = Callable[[list[OnEventCallback]], None]
MainFunction = Callable[
    [list[threading.Event]],
    Awaitable[
        fs.FileSystemOperations,
    ],
]


def task_from_blocking(blocking_func):
    return asyncio.create_task(
        asyncio.to_thread(blocking_func),
    )


def wait_ev(ev: threading.Event, on_done=lambda: None, event_id: str = ""):
    def _inner():
        ev.wait()
        on_done()

    return _inner


def run_fs(
    fs_func: Callable[
        [MainFunction, list[threading.Event], threading.Event, str],
        Awaitable[
            None,
        ],
    ],
    main_function: MainFunction,
    events: list[threading.Event],
    exit_ev: threading.Event,
    destination: str,
):
    event_loop = asyncio.new_event_loop()
    event_loop.run_until_complete(
        fs_func(
            main_function,
            events,
            exit_ev,
            destination,
        )
    )


async def _main(
    main_func: MainFunction,
    events: list[threading.Event],
    exit_event: threading.Event,
    destination: str,
):
    """Will be called from a separate process"""

    async def noop(events_cbs: list[OnEventCallback]):
        return None

    env = {
        "on_event": noop,
    }

    fs1 = main_func(events)

    pyfuse3_asyncio.enable()

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add("fsname=test_tgmount")
    # fuse_options.add("debug")

    pyfuse3.init(fs1, destination, fuse_options)

    pyfuse_task = asyncio.create_task(pyfuse3.main(min_tasks=10))

    # wait_ev_task = task_from_blocking(wait_ev(ev0))
    # async def on_event():
    #     await wait_ev_task
    #     await env["on_event"]()

    # main_task = asyncio.create_task(
    #     asyncio.wait(
    #         [pyfuse_task, on_event()],
    #         return_when=asyncio.ALL_COMPLETED,
    #     )
    # )

    def exit():
        exit_event.set()
        pyfuse3.close(unmount=True)

    exit_ev_task = task_from_blocking(wait_ev(exit_event, exit))

    await asyncio.wait(
        [exit_ev_task, pyfuse_task],
        return_when=asyncio.FIRST_COMPLETED,
    )


def mountfs(
    main_function: MainFunction,
    # fs_func: Callable[[threading.Event, threading.Event, str], Awaitable[None]],
    *,
    mnt_dir: str,
):
    mnt_dir = str(mnt_dir)

    mp = multiprocessing.get_context("forkserver")

    with mp.Manager() as mgr:
        cross_process_event = mgr.Event()
        exit_event = mgr.Event()

        mount_process = mp.Process(
            target=run_fs,
            args=(
                _main,
                main_function,
                cross_process_event,
                exit_event,
                mnt_dir,
            ),
        )

        mount_process.start()

        try:
            wait_for_mount(mount_process, mnt_dir)
            yield MountContext(
                mnt_dir,
                exit_event,
                events=[cross_process_event],
            )
            exit_event.set()
        except:
            cleanup(mount_process, mnt_dir)
            raise
        else:
            umount(mount_process, mnt_dir)

import logging
import multiprocessing
import os
import threading
from dataclasses import dataclass
from multiprocessing.managers import SyncManager
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Generator,
    Generic,
    Mapping,
    Optional,
    TypedDict,
    TypeVar,
)
from tgmount import tglog


import tgmount.fs as fs
from tgmount.fs import logger
from tgmount.main.util import mount_ops

from .mount import cleanup, umount, wait_for_mount
from .asyncio import wait_ev, task_from_blocking
from ..logger import logger as _logger

Props = Mapping


P = TypeVar("P", bound=Props)


OnEventCallback = Callable[[], Awaitable[None]]
OnEventCallbackSet = Callable[[threading.Event, OnEventCallback], None]

MainFunction = Callable[
    [P, OnEventCallbackSet],
    Awaitable[fs.FileSystemOperations],
]

GetProps = Callable[["MountContext[P]"], P]

logger = _logger.getChild("spawn")


@dataclass
class MountContext(Generic[P]):
    tmpdir: str
    mgr: SyncManager
    exit_event: threading.Event

    props: Optional[P] = None

    def path(self, *p: str):
        return os.path.join(self.tmpdir, *p)

    def listdir(self, *p: str):
        return set(os.listdir(self.path(*p)))

    def exists(self, *p: str):
        return os.path.exists(self.path(*p))


async def __inner_mount_fs(
    main_function: MainFunction,
    props: Props,
    *,
    mnt_dir: str,
    min_tasks: int
    # on_event: OnEventCallbackSet,
):
    import asyncio

    events: list[tuple[threading.Event, OnEventCallback]] = []

    def on_event(ev: threading.Event, callback: OnEventCallback):
        events.append((ev, callback))

    ops = await main_function(props, on_event)

    mount_task = asyncio.create_task(
        mount_ops(
            ops,
            mount_dir=mnt_dir,
            min_tasks=min_tasks,
        )
    )

    async def on_event_wait(ev_task: asyncio.Task, cb: OnEventCallback):
        await ev_task
        await cb()

    ev_tasks = [
        asyncio.create_task(
            on_event_wait(
                task_from_blocking(wait_ev(ev)),
                cb,
            )
        )
        for ev, cb in events
    ]

    return await asyncio.wait(
        [mount_task, *ev_tasks],
        return_when=asyncio.ALL_COMPLETED,
    )


def __spawn_fs_ops_inner_main(
    main_function: MainFunction,
    props: Props,
    *,
    mnt_dir: str,
    min_tasks: int,
    exit_event: threading.Event,
):
    import asyncio

    from tgmount.main.util import run_main

    async def _async_inner():
        def timeout():
            exit_event.wait()

        mount_task = asyncio.create_task(
            __inner_mount_fs(main_function, props, mnt_dir=mnt_dir, min_tasks=min_tasks)
        )

        wait_for_exit_task = asyncio.create_task(asyncio.to_thread(timeout))

        await asyncio.wait(
            [mount_task, wait_for_exit_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

    run_main(_async_inner)


def __spawn_mount_process(
    main_function: MainFunction,
    props: Props | Callable[[MountContext], Props],
    *,
    mnt_dir: str,
    min_tasks: int,
):
    logger.debug("spawn_process()")

    mp = multiprocessing.get_context("fork")

    with mp.Manager() as mgr:
        exit_event = mgr.Event()
        ctx = MountContext(mnt_dir, mgr, exit_event=exit_event)

        _props: Props = props(ctx) if isinstance(props, Callable) else props
        ctx.props = _props

        mount_process = mp.Process(
            target=__spawn_fs_ops_inner_main,
            args=(main_function, _props),
            kwargs={
                "exit_event": exit_event,
                "mnt_dir": mnt_dir,
                "min_tasks": min_tasks,
            },
            daemon=True,
        )

        mount_process.start()

        try:
            wait_for_mount(mount_process, mnt_dir)
            yield ctx

        except:
            cleanup(mount_process, mnt_dir)
            raise
        else:
            umount(mount_process, mnt_dir)


def spawn_fs_ops(
    main_function: MainFunction[Any],
    props: P | Callable[[MountContext], P],
    mnt_dir: str,  # type: ignore
    min_tasks: int,
) -> Generator[MountContext[P], None, None]:
    """spawns a separate proces mounting vfs root returned by `main_function`"""
    for m in __spawn_mount_process(
        main_function, props, mnt_dir=mnt_dir, min_tasks=min_tasks
    ):
        yield m
        m.exit_event.set()

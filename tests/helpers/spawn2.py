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
    Mapping,
    Optional,
    TypedDict,
    TypeVar,
)

import pytest
import pytest_asyncio
import tgmount.fs as fs
from tgmount.main.util import mount_ops
from tgmount.vfs.types.dir import DirLike

from ..helpers.mount import cleanup, umount, wait_for_mount

Props = Mapping


@dataclass
class MountContext:
    tmpdir: str
    mgr: SyncManager
    cross_process_event: Optional[threading.Event] = None
    exit_event: Optional[threading.Event] = None

    props: Optional[Props] = None

    def path(self, *p: str):
        return os.path.join(self.tmpdir, *p)


P = TypeVar("P", bound=Props)

MainFunction = Callable[
    [P],
    Awaitable[fs.FileSystemOperations],
]

MountFsFunction = Callable[[Props, str], Coroutine[None, Any, Any]]


async def __inner_mount_fs(
    main_function: MainFunction,
    props: Props,
    *,
    mnt_dir: str,
):
    ops = await main_function(props)

    return await mount_ops(
        ops,
        mnt_dir,
    )


def __spawn_fs_ops_inner_main(
    main_function: MainFunction,
    props: Props,
    *,
    mnt_dir: str,
    exit_event: threading.Event,
):
    import asyncio

    from tgmount.main.util import run_main

    async def _async_inner():
        def timeout():
            exit_event.wait()

        mount_task = asyncio.create_task(
            __inner_mount_fs(
                main_function,
                props,
                mnt_dir=mnt_dir,
            )
        )
        wait_for_exit_task = asyncio.create_task(asyncio.to_thread(timeout))

        await asyncio.wait(
            [mount_task, wait_for_exit_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

    run_main(_async_inner)


def __spawn_mount_process(
    # proccess_function: Callable[
    #     [MountFsFunction, Props, threading.Event],
    #     None,
    # ],
    # mount_fs: MountFsFunction,
    main_function: MainFunction,
    props: Props | Callable[[MountContext], Props],
    *,
    mnt_dir: str,
):
    print("spawn_process()")
    #         __spawn_fs_ops_inner_main,
    # __inner_mount_fs,
    mp = multiprocessing.get_context("spawn")

    with mp.Manager() as mgr:
        exit_event = mgr.Event()
        ctx = MountContext(mnt_dir, mgr, exit_event=exit_event)

        _props: Props = props(ctx) if isinstance(props, Callable) else props
        ctx.props = _props

        mount_process = mp.Process(
            target=__spawn_fs_ops_inner_main,
            args=(main_function, props),
            kwargs={"exit_event": exit_event, "mnt_dir": mnt_dir},
            daemon=True,
        )

        mount_process.start()

        try:
            wait_for_mount(mount_process, mnt_dir)
            yield ctx
            # ev.set()
            # mount_process.join()
            # mount_process.close()

        except:
            cleanup(mount_process, mnt_dir)
            raise
        else:
            umount(mount_process, mnt_dir)


def spawn_fs_ops(
    main_function: MainFunction[Props],
    props: Props | Callable[[MountContext], Props],
    mnt_dir: str,  # type: ignore
):
    """spawns a separate proces mounting vfs root returned by `main_function`"""
    for m in __spawn_mount_process(
        main_function,
        props,
        mnt_dir=mnt_dir,
    ):
        yield m
        m.exit_event.set()

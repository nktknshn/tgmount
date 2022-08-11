import multiprocessing
import threading
from typing import Awaitable, Callable, Coroutine

import pytest
import pytest_asyncio
import tgmount.fs as fs
from tgmount.main.util import mount_ops
from tgmount.vfs.types.dir import DirLike

from ..fs.util import cleanup, umount, wait_for_mount
from ..fs.run import Fixtures


async def __inner_main_root(
    main_function: Callable[[], Awaitable[DirLike]], mnt_dir: str, *args
):
    vfs_root = await main_function(*args)

    return await mount_ops(
        fs.FileSystemOperations(vfs_root),
        mnt_dir,
    )


def __spawn_root_inner_main(ev: threading.Event, main_function: Callable, *args):
    import asyncio

    from tgmount.main.util import run_main

    async def _async_inner():
        def timeout():
            ev.wait()

        mount_task = asyncio.create_task(main_function(*args))
        timeout_task = asyncio.create_task(asyncio.to_thread(timeout))

        await asyncio.wait(
            [mount_task, timeout_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

    run_main(_async_inner)


def spawn_vfs_root(
    main_function: Callable[[...], Awaitable[DirLike]], *args, mnt_dir: str  # type: ignore
):
    """spawns a separate proces mounting vfs root returned by `main_function`"""
    for ev, m in spawn_mount_process(
        __spawn_root_inner_main,
        mnt_dir,
        __inner_main_root,
        main_function,
        mnt_dir,
        *args
    ):
        yield m
        ev.set()


def __spawn_fs_ops_inner_main(ev: threading.Event, main_function: Callable, *args):
    import asyncio

    from tgmount.main.util import run_main

    async def _async_inner():
        def timeout():
            ev.wait()

        mount_task = asyncio.create_task(main_function(*args))
        timeout_task = asyncio.create_task(asyncio.to_thread(timeout))

        await asyncio.wait(
            [mount_task, timeout_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

    run_main(_async_inner)


async def __inner_main_fs_ops(
    main_function: Callable[[], Awaitable[fs.FileSystemOperations]], mnt_dir: str, *args
):
    ops = await main_function(*args)

    return await mount_ops(
        ops,
        mnt_dir,
    )


def spawn_fs_ops(
    main_function: Callable[[...], Awaitable[fs.FileSystemOperations]], *args, mnt_dir: str  # type: ignore
):
    """spawns a separate proces mounting vfs root returned by `main_function`"""
    for ev, m in spawn_mount_process(
        __spawn_fs_ops_inner_main,
        mnt_dir,
        __inner_main_fs_ops,
        main_function,
        mnt_dir,
        *args
    ):
        yield m
        ev.set()


def spawn_mount_process(
    proccess_function: Callable[
        [threading.Event, ...],
        None,
    ],
    mnt_dir: str,
    *args
):
    print("spawn_process()")

    mp = multiprocessing.get_context("spawn")
    with mp.Manager() as mgr:
        ev = mgr.Event()
        mount_process = mp.Process(
            target=proccess_function, args=(ev, *args), daemon=True
        )

        mount_process.start()

        try:
            wait_for_mount(mount_process, mnt_dir)
            yield ev, Fixtures(None, mnt_dir)
            # ev.set()
            # mount_process.join()
            # mount_process.close()

        except:
            cleanup(mount_process, mnt_dir)
            raise
        else:
            umount(mount_process, mnt_dir)

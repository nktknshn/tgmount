import io
import os
from typing import Awaitable, Callable, Coroutine
import pytest
import tgmount.fs as fs
import tgmount.tgclient as tg
from tests.fs.run import spawn_process
from tgmount.main.util import mount_ops, read_tgapp_api
from tgmount.tg_vfs.source import TelegramFilesSource
from tgmount.vfs.types.dir import DirLike

import threading


@pytest.fixture
def mnt_dir(tmpdir):
    return str(tmpdir)


def __inner_main(ev: threading.Event, main_function: Callable, *args):
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


def spawn_tgmount(main_function: Callable[[str], Coroutine], mnt_dir: str, *args):
    return spawn_process(__inner_main, mnt_dir, main_function, mnt_dir, *args)


async def tgclient(tgapp_api: tuple[int, str]):
    client = tg.TgmountTelegramClient("tgfs", tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client


async def get_client_source(Source=TelegramFilesSource):
    client = await tgclient(read_tgapp_api())
    storage = Source(client)

    return client, storage


async def __inner_main_root(
    main_function: Callable[[], Awaitable[DirLike]], mnt_dir: str, *args
):
    root = await main_function(*args)
    return await mount_ops(fs.FileSystemOperations(root), mnt_dir)


def spawn_root(
    main_function: Callable[[...], Awaitable[DirLike]], *args, mnt_dir: str  # type: ignore
):
    for ev, m in spawn_process(
        __inner_main, mnt_dir, __inner_main_root, main_function, mnt_dir, *args
    ):
        yield m
        ev.set()

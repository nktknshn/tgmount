import io
import os
import threading
from typing import Awaitable, Callable, Coroutine

import pytest
import pytest_asyncio
import tgmount.fs as fs
import tgmount.tgclient as tg
from tgmount import vfs
from tgmount.main.util import read_tgapp_api
from tgmount.vfs.types.dir import DirLike


@pytest.fixture()
def mnt_dir(tmpdir):
    return str(tmpdir)


@pytest.fixture()
def fs_tree1() -> vfs.DirContentSourceTree:
    tc = vfs.text_content
    return {
        "dir1": {
            "file1.txt": tc("file1.txt content"),
            "file2.txt": tc("file2.txt content"),
        },
        "dir2": {
            "file3.txt": tc("file3.txt content"),
            "file4.txt": tc("file4.txt content"),
            "dir2_dir3": {
                "file5.txt": tc("file5.txt content"),
            },
        },
        "dir3": vfs.dir_content(
            vfs.vfile("dir3_file1.txt", tc("dir3_file1.txt content"))
        ),
    }


@pytest_asyncio.fixture
def tgapp_api():
    return read_tgapp_api()


@pytest_asyncio.fixture
async def tgclient_second(tgapp_api: tuple[int, str]):
    client = tg.TgmountTelegramClient("second_session", tgapp_api[0], tgapp_api[1])
    await client.auth()
    yield client
    await client.disconnect()

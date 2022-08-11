import io
import os
from typing import Awaitable, Callable, Coroutine
import pytest
import pytest_asyncio
import tgmount.fs as fs
import tgmount.tgclient as tg
from tgmount.main.util import read_tgapp_api
from tgmount.tg_vfs.source import TelegramFilesSource
from tgmount.vfs.types.dir import DirLike

import threading


@pytest.fixture
def mnt_dir(tmpdir):
    return str(tmpdir)


@pytest_asyncio.fixture
def tgapp_api():
    return read_tgapp_api()


@pytest_asyncio.fixture
async def tgclient_second(tgapp_api: tuple[int, str]):
    client = tg.TgmountTelegramClient("second_session", tgapp_api[0], tgapp_api[1])
    await client.auth()
    yield client
    await client.disconnect()


async def tgclient(tgapp_api: tuple[int, str], session_name="tgfs"):
    client = tg.TgmountTelegramClient(session_name, tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client


async def get_client_with_source(Source=TelegramFilesSource):
    client = await tgclient(read_tgapp_api())
    storage = Source(client)

    return client, storage

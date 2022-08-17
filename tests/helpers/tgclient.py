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


async def get_tgclient(
    tgapp_api: tuple[int, str],
    session_name="tgfs",
    *,
    client_cls=tg.TgmountTelegramClient
):
    client = client_cls(session_name, tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client


async def get_client_with_source(Source=tg.TelegramFilesSource, session_name="tgfs"):
    client = await get_tgclient(read_tgapp_api())
    source = Source(client)

    return client, source

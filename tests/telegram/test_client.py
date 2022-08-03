import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

import pytest
import pytest_asyncio
import tgmount.fs as fs
from telethon import types
from tests.fs.run import mountfs
from tgmount import vfs
from tgmount.tg_vfs.source import (
    TelegramFilesSource,
)
from tgmount.tg_vfs.util import get_music_file
from tgmount.tgclient import TgmountTelegramClient
from tgmount.main.util import read_tgapp_api


@pytest.fixture
def tgapp_api():
    return read_tgapp_api()


Client = TgmountTelegramClient


@pytest_asyncio.fixture
async def tgclient(tgapp_api):
    client = TgmountTelegramClient("tgfs", tgapp_api[0], tgapp_api[1])

    await client.auth()

    yield client

    cor = client.disconnect()

    if cor is not None:
        await cor


@pytest.mark.asyncio
async def test_tg1(tgclient: Client):
    message = await tgclient.get_messages_typed("D1SMBD1D", limit=10)

    assert len(message) == 10


@pytest.mark.asyncio
async def test_tg2(event_loop, tmpdir: str, tgclient: Client):
    count = 10
    storage = TelegramFilesSource(tgclient)
    messages = await tgclient.get_messages_typed(
        "D1SMBD1D", limit=count, filter=types.InputMessagesFilterMusic
    )

    assert len(messages) == count

    files = []
    mfs = []

    for msg in messages:
        mf = get_music_file(msg)

        if mf is None:
            print(msg)
            continue

        fc = await storage.file_content(mf.message, mf.document)

        mfs.append((f"{mf.message.chat_id}_{mf.message.id}_{mf.file_name}", mf))
        files.append((f"{mf.message.chat_id}_{mf.message.id}_{mf.file_name}", fc))

    assert len(files) == count

    mf_by_name = dict(mfs)
    vfs_root = vfs.root(vfs.create_dir_content_from_tree({"D1SMBD1D": dict(files)}))

    for m in mountfs(str(tmpdir), fs.FileSystemOperations(vfs_root)):
        subfiles = os.listdir(m.path("D1SMBD1D/"))

        assert len(subfiles) == count

        for sf in subfiles:
            print(mf_by_name[sf])

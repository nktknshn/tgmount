import asyncio
import os

import pytest
import pytest_asyncio
import telethon
from telethon import types, errors, network
import logging
from tgmount import tgclient, vfs, logging as log

from tgmount.tgclient import guards

from ..helpers.fixtures import tgapp_api
from ..helpers.tgclient import get_tgclient

TESTING_CHANNEL = "tgmounttestingchannel"


class LaggingClient(tgclient.TgmountTelegramClient):
    def __init__(self, session_user_id, api_id, api_hash):
        super().__init__(session_user_id, api_id, api_hash)

    # async def iter_download(self, *args, **kwargs):
    #     async for chunk in super().iter_download(*args, **kwargs):
    #         yield chunk


class LagginConnection(network.ConnectionTcpFull):
    async def recv(self):
        await asyncio.sleep(1)
        return await super().recv()


@pytest.mark.asyncio
async def test_source1(tgapp_api: tuple[int, str], caplog):
    caplog.set_level(logging.DEBUG)
    log.init_logging(True)

    client = tgclient.TgmountTelegramClient(
        "tgfs",
        *tgapp_api,
        connection=LagginConnection,
        # timeout=
    )

    await client.auth()

    source = tgclient.TelegramFilesSource(client)

    [msg0] = await client.get_messages_typed(
        TESTING_CHANNEL,
        limit=1,
        filter=types.InputMessagesFilterDocument,
    )

    assert guards.is_downloadable(msg0)

    fc = source.file_content(msg0)
    c = await vfs.read_file_content_bytes(fc)

    assert c

    if cor := client.disconnect():
        await cor

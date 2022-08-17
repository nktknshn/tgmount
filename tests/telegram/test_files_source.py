import asyncio
import os

import pytest
import pytest_asyncio
import telethon
from telethon import types, errors
import logging
from tgmount import tgclient, vfs, logging as log

from tgmount.tgclient import guards

from ..helpers.fixtures import tgapp_api
from ..helpers.tgclient import get_tgclient

TESTING_CHANNEL = "tgmounttestingchannel"


class LaggingClient(tgclient.TgmountTelegramClient):
    def __init__(self, session_user_id, api_id, api_hash, proxy=None):
        super().__init__(session_user_id, api_id, api_hash, proxy=proxy)

    async def iter_download(self, *args, **kwargs):
        async for chunk in super().iter_download(*args, **kwargs):
            yield chunk


@pytest.mark.asyncio
async def test_source1(tgapp_api, caplog):
    caplog.set_level(logging.DEBUG)
    log.init_logging(True)

    client = await get_tgclient(
        tgapp_api,
        client_cls=LaggingClient,
    )
    source = tgclient.TelegramFilesSource(client)

    [msg0] = await client.get_messages_typed(
        TESTING_CHANNEL, limit=1, filter=types.InputMessagesFilterDocument
    )

    assert guards.is_downloadable(msg0)

    fc = source.file_content(msg0)
    c = await vfs.read_file_content_bytes(fc)

    assert c

    await client.disconnect()

import asyncio
import logging
import os
import threading
from typing import Iterable, Mapping, TypedDict

import pyfuse3
import pytest
import pytest_asyncio
import telethon
import tgmount.fs as fs
import tgmount.tgclient as tg
import tgmount.vfs as vfs
from telethon import events, types
from tests.helpers.tgclient import get_client_with_source
from tgmount.tglog import init_logging
from tgmount.tgclient import guards

from ..helpers.asyncio import task_from_blocking, wait_ev, wait_ev_async
from ..helpers.fixtures import mnt_dir, tgapp_api, tgclient_second
from ..helpers.spawn import MountContext, spawn_fs_ops

Message = telethon.tl.custom.Message
Document = telethon.types.Document
Client = tg.TgmountTelegramClient

InputMessagesFilterDocument = telethon.tl.types.InputMessagesFilterDocument

TESTING_CHANNEL = "tgmounttestingchannel"


# Props = Mapping
Props = TypedDict("Props", debug=bool, ev0=threading.Event)


async def main_test1(
    props: Props,
    on_event,
):
    init_logging(props["debug"])

    client, source = await get_client_with_source()

    files = tg_vfs.FileFactoryDefault(source)

    messages = await client.get_messages_typed(
        TESTING_CHANNEL,
        limit=100,
        reverse=True,
    )

    def create_root(messages: Iterable[Message]) -> vfs.VfsRoot:
        return vfs.root(
            {
                "tmtc": files.create_dir_content_source(
                    filter(guards.MessageWithDocument.guard, messages)
                ),
            }
        )

    vfs_root = create_root(messages[:])

    ops = fs.FileSystemOperationsUpdatable(vfs_root)

    @client.on(events.NewMessage(chats=TESTING_CHANNEL))
    async def event_handler_new_message(event: events.NewMessage.Event):

        messages.append(event.message)
        await ops.update_root(create_root(messages[:]))
        # ops.print_stats()

    @client.on(events.MessageEdited(chats=TESTING_CHANNEL))
    async def event_handler_message_edited(event: events.MessageEdited.Event):
        print(event)

    @client.on(events.MessageDeleted(chats=TESTING_CHANNEL))
    async def event_handler_message_deleted(event: events.MessageDeleted.Event):
        print(event)

    return ops


def get_props(ctx: MountContext) -> Props:
    return {
        "debug": False,
        "ev0": ctx.mgr.Event(),
    }


@pytest.mark.asyncio
async def test_fs_tg_test1(mnt_dir, caplog, tgclient_second: Client):

    caplog.set_level(logging.INFO)

    messages = await tgclient_second.get_messages_typed(
        TESTING_CHANNEL,
        limit=10,
    )

    assert len(messages) == 10

    for ctx in spawn_fs_ops(
        main_test1,
        props=get_props,
        mnt_dir=mnt_dir,
    ):

        subfiles = os.listdir(ctx.path("tmtc/"))
        len1 = len(subfiles)

        assert len1 > 0

        msg0 = await tgclient_second.send_message(
            TESTING_CHANNEL,
            file="tests/fixtures/Hummingbird.jpg",
            force_document=True,
        )

        # ctx.props["ev0"].set()

        await asyncio.sleep(3)

        subfiles = os.listdir(ctx.path("tmtc/"))
        assert len(subfiles) == len1 + 1

        await tgclient_second.delete_messages(TESTING_CHANNEL, [msg0.id])

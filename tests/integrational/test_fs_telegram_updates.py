import asyncio
import io
import logging
import os
from typing import Iterable

import aiofiles as af
import pyfuse3
import pytest
import pytest_asyncio
import telethon
import tgmount.fs as fs
import tgmount.tgclient as tg
import tgmount.vfs as vfs
import tgmount.zip as z
from telethon import events, types
from tgmount.logging import init_logging
from tgmount.tg_vfs import FileFactory
from tgmount.vfs.dir import FsSourceTree

from .spawn import spawn_fs_ops
from .util import get_client_with_source, mnt_dir, tgapp_api, tgclient, tgclient_second

Message = telethon.tl.custom.Message
Document = telethon.types.Document
Client = tg.TgmountTelegramClient

InputMessagesFilterDocument = telethon.tl.types.InputMessagesFilterDocument

TESTING_CHANNEL = "tgmounttestingchannel"


class FileSystemOperationsUpdatable(fs.FileSystemOperations):
    def __init__(self, root: vfs.DirLike):
        super().__init__(root)

    def print_stats(self):
        print("inodes")
        print(self._inodes._inodes.keys())

        print("fhs")
        print(self._handers._fhs.keys())

    async def update_root(self, root: vfs.DirLike):

        for inode in reversed(self._inodes.get_inodes()):
            # print(f"inode={inode}")
            kids = self._inodes.get_items_by_parent_dict(inode)

            if kids is None:
                continue

            for k, v in kids.items():
                print(f"invalidate_entry({inode}, {k})")
                pyfuse3.invalidate_entry_async(inode, k)

        # pyfuse3.invalidate_inode(pyfuse3.ROOT_INODE)

        # for inode in self._inodes._inodes.keys():
        #     pyfuse3.invalidate_inode(inode)

        self._init_handers(self._handers._last_fh + 1)
        self._init_root(root)

        print("update_root() done")


async def main_test1(debug):
    init_logging(debug)
    client, source = await get_client_with_source()
    files = FileFactory(source)
    messages = await client.get_messages_typed(
        TESTING_CHANNEL,
        limit=100,
        reverse=True,
    )

    def create_root(messages: Iterable[Message]) -> vfs.VfsRoot:
        return vfs.root(
            {
                "tmtc": files.create_tree(
                    filter(tg.guards.MessageWithDocument.guard, messages)
                ),
            }
        )

    vfs_root = create_root(messages[:])

    ops = FileSystemOperationsUpdatable(vfs_root)

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


@pytest.mark.asyncio
async def test_fs_tg_test1(mnt_dir, caplog, tgclient_second: Client):

    caplog.set_level(logging.DEBUG)

    messages = await tgclient_second.get_messages_typed(
        TESTING_CHANNEL,
        limit=10,
    )

    assert len(messages) == 10

    for ctx in spawn_fs_ops(main_test1, True, mnt_dir=mnt_dir):

        subfiles = os.listdir(ctx.path("tmtc/"))
        len1 = len(subfiles)
        assert len1 > 0

        msg0 = await tgclient_second.send_message(
            TESTING_CHANNEL,
            file="tests/fixtures/Hummingbird.jpg",
            force_document=True,
        )

        await asyncio.sleep(3)

        subfiles = os.listdir(ctx.path("tmtc/"))
        assert len(subfiles) == len1 + 1

        await tgclient_second.delete_messages(TESTING_CHANNEL, [msg0.id])

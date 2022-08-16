import asyncio
import io
import logging
import os

import aiofiles as af
import pytest
import pytest_asyncio
import telethon
import tgmount.tgclient as tg
import tgmount.vfs as vfs
import tgmount.zip as z
import tgmount.fs as fs

from tgmount.logging import init_logging
from tgmount.tg_vfs.source import TelegramFilesSource
from tgmount.vfs import FsSourceTree

from ..helpers.fixtures import get_client_with_source
from ..helpers.spawn2 import spawn_fs_ops

Message = telethon.tl.custom.Message
Document = telethon.types.Document
Client = tg.TgmountTelegramClient

InputMessagesFilterDocument = telethon.tl.types.InputMessagesFilterDocument


async def messages_to_files_tree(
    source: TelegramFilesSource,
    messages: list[Message],
) -> FsSourceTree:
    return dict(
        [
            (
                msg.file.name,
                source.file_content(msg, msg.document),
            )
            for msg in messages
            if msg.file.name is not None
        ]
    )


async def main_test1(props, _):
    init_logging(props["debug"])

    client, storage = await get_client_with_source()
    messages = await client.get_messages_typed(
        "tgmounttestingchannel",
        limit=3,
        reverse=True,
        filter=InputMessagesFilterDocument,
    )

    return fs.FileSystemOperations(
        vfs.root({"tmtc": await messages_to_files_tree(storage, messages)})
    )


@pytest.mark.asyncio
async def test_fs_tg_test1(mnt_dir, caplog):

    caplog.set_level(logging.DEBUG)

    amount = 512 * 1024

    f = await af.open("tests/fixtures/bandcamp1.zip", "rb")
    bc1 = await f.read1(amount)

    for m in spawn_fs_ops(main_test1, {"debug": False}, mnt_dir=mnt_dir):

        subfiles = os.listdir(m.path("tmtc/"))
        assert len(subfiles) == 3

        fopen1 = lambda: af.open(m.path("tmtc/bandcamp1.zip"), "rb")
        fopen2 = lambda: af.open(m.path("tmtc/linux_zip_stored1.zip"), "rb")

        async def read(f, amount, msg, offset=None):
            if offset is not None:
                await f.seek(offset)

            print(f"reading {msg} {amount}")
            res = await f.read(amount)
            print(f"done reading {msg} {amount}")
            return res

        [f1, f2, f3, f4, f5, f6] = await asyncio.gather(
            fopen1(), fopen1(), fopen1(), fopen2(), fopen2(), fopen2()
        )

        [r1, r2, r3, r4, r5, r6] = await asyncio.gather(
            read(f1, amount, "f1"),
            read(f2, amount, "f2"),
            read(f3, amount * 2, "f3", 30000),
            read(f4, amount, "f4"),
            read(f5, amount, "f5"),
            read(f6, amount * 2, "f6", 30000),
        )

        assert bc1 == r1
        assert bc1 == r2


class TackingSource(TelegramFilesSource):
    def __init__(
        self, client: tg.TgmountTelegramClient, request_size: int = 128 * 1024
    ) -> None:
        super().__init__(client, request_size)

        self.total_asked = 0

    async def item_read_function(
        self, message: Message, item: Document, offset: int, limit: int
    ) -> bytes:
        self.total_asked += limit

        if limit > 2187200:
            pass

        print(f"offset={offset} limit={limit}")
        print(f"self.total_asked = {self.total_asked}")
        return await super().item_read_function(message, item, offset, limit)


# async def main_test2(props, _):
#     init_logging(props["debug"])

#     client, storage = await get_client_with_source(Source=TackingSource)

#     messages = await client.get_messages_typed(
#         "tgmounttestingchannel",
#         limit=3,
#         reverse=True,
#         filter=InputMessagesFilterDocument,
#     )

#     return vfs.root(
#         z.zips_as_dirs(
#             vfs.dir_from_tree({"tmtc": await messages_to_files_tree(storage, messages)})
#         )
#     )


# @pytest.mark.asyncio
# async def test_fs_tg_test2(mnt_dir, caplog):

#     caplog.set_level(logging.DEBUG)

#     amount = 512 * 1024

#     f0 = await af.open("tests/fixtures/1/Forlate.mp3", "rb")

#     await f0.seek(4376046 // 2)
#     bs0 = await f0.read(1024 * 256)

#     for m in spawn_vfs_root(main_test2, False, mnt_dir=mnt_dir):

#         with open(
#             m.path(
#                 "tmtc/linux_zip_stored1.zip/Forlate.mp3",
#             ),
#             "rb",
#         ) as f:
#             print(f"pre seek")
#             f.seek(4376046 // 2)
#             print(f"pre read")
#             bs = f.read(1024 * 256)

#             print(f"bs = {len(bs)} bytes")

#             assert bs0 == bs

import argparse
import logging
from typing import Any, Awaitable, Callable, Optional, Protocol, TypeGuard, TypeVar

from telethon import types
from telethon.tl.custom import message
from telethon.tl.custom.file import File
from typing_extensions import Required

from tgmount import fs, vfs
from tgmount import zip as z

from tgmount.cache import CacheFactoryMemory, CachingDocumentsSource
from tgmount.logging import init_logging
from tgmount.main.util import mount_ops, read_tgapp_api, run_main
from tgmount.tg_vfs import TelegramFilesSource
from tgmount.tgclient import TelegramSearch, TgmountTelegramClient, guards
from tgmount.vfs import FsSourceTree, text_content

logger = logging.getLogger("tgvfs")


async def tgclient(tgapp_api: tuple[int, str], session_name="tgfs"):
    client = TgmountTelegramClient(session_name, tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client


async def create_test(
    telegram_id: str,
    messages_source: TelegramSearch,
    documents: TelegramFilesSource,
    limit=3000,
) -> FsSourceTree:

    cache = CacheFactoryMemory(blocksize=128 * 1024)
    caching = CachingDocumentsSource(documents, cache)

    messages = await messages_source.get_messages_typed(
        telegram_id,
        limit=limit,
    )

    texts = [
        (f"{msg.id}.txt", text_content(msg.message))
        for msg in messages
        if guards.MessageWithText.guard(msg)
    ]

    photos = [
        (f"{msg.id}_photo.jpeg", documents.content(msg))
        for msg in messages
        if guards.MessageWithPhoto.guard(msg)
    ]

    videos = [
        (f"{msg.id}_document{msg.file.ext}", documents.content(msg))
        for msg in messages
        if guards.MessageWithVideo.guard(msg)
    ]

    music = [
        (f"{msg.id}_{msg.file.name}", documents.content(msg))
        for msg in messages
        if guards.MessageWithMusic.guard(msg)
    ]

    zips = [
        (f"{msg.id}_{msg.file.name}", caching.content(msg))
        for msg in messages
        if guards.MessageWithDocument.guard(msg)
        and msg.file.name is not None
        and msg.file.name.endswith(".zip")
    ]

    return {
        "texts": texts,
        "photos": photos,
        "videos": videos,
        "music": music,
        "zips": z.zips_as_dirs(dict(zips)),
    }


async def mount():
    init_logging(debug=True)

    client = await tgclient(read_tgapp_api())

    messages_source = client
    documents_source = TelegramFilesSource(client)

    vfs_root = vfs.root(
        {
            "test": await create_test(
                "tgmounttestingchannel",
                messages_source,
                documents_source,
            ),
        }
    )

    ops = fs.FileSystemOperations(vfs_root)

    await mount_ops(ops, "/home/hrn/mnt/tgmount1")


if __name__ == "__main__":
    run_main(mount)

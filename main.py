import argparse
import logging
from typing import Awaitable, Callable, Optional, TypeVar, Protocol

from telethon import types

from tgmount import fs, vfs
from tgmount import zip as z
from tgmount.logging import init_logging
from tgmount.main.util import mount_ops, read_tgapp_api, run_main
from tgmount.tg_vfs.source import (
    TelegramFilesSource,
)

# from tgmount.cache.factory import DocumentsCacheFactory
from tgmount.cache.source import (
    CachingDocumentsSource,
)
from tgmount.tg_vfs.util import get_document
from tgmount.tgclient import TgmountTelegramClient, Message, Document, DocId

from tgmount.cache import (
    CacheBlockStorageMemory,
    CacheBlockReaderWriter,
    CacheFactoryProto,
    CacheBlockStorageFile,
)
from tgmount.tgclient.search import TelegramSearch
from tgmount.tgclient.types import TotalListTyped
from tgmount.vfs.dir import FsSourceTree
from tgmount.vfs.types.file import FileContent

logger = logging.getLogger("tgvfs")

# def get_parser():
#     parser = argparse.ArgumentParser()
#     # parser.add_argument('--config', 'mount config', required=True)
#     parser.add_argument("--max-tasks", type=int, default=2)

#     return parser


async def tgclient(tgapp_api: tuple[int, str], session_name="tgfs"):
    client = TgmountTelegramClient(session_name, tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client


T = TypeVar("T")


class DocumentsCacheFactoryMemory(CacheFactoryProto[CacheBlockReaderWriter]):
    """This class is gonna decide how to store documents cache if needed"""

    def __init__(self, blocksize: int) -> None:
        self._blocksize = blocksize
        self._caches: dict[
            DocId, tuple[CacheBlockStorageMemory, CacheBlockReaderWriter]
        ] = {}

    async def total_stored(self) -> int:
        total = 0
        for k, (storage, reader) in self._caches.items():
            total += await storage.total_stored()

        return total

    async def get_cache(
        self,
        message: Message,
        document: Document,
    ) -> CacheBlockReaderWriter:

        if document.id in self._caches:
            return self._caches[document.id][1]

        blocks_storage = CacheBlockStorageMemory(
            blocksize=self._blocksize,
            total_size=document.size,
        )

        reader = CacheBlockReaderWriter(
            blocks_storage=blocks_storage,
        )

        self._caches[document.id] = (blocks_storage, reader)

        return reader


class DocumentsCacheFactoryFiles(CacheFactoryProto):
    """This class is gonna decide how to store documents cache if needed"""

    def __init__(self) -> None:
        self.caches: dict[
            DocId, tuple[CacheBlockStorageMemory, CacheBlockReaderWriter]
        ] = {}

    async def total_stored(self) -> int:
        total = 0
        for k, (storage, reader) in self.caches.items():
            total += await storage.total_stored()

        return total

    async def get_cache_files(
        self,
        message: Message,
        document: Document,
    ) -> CacheBlockReaderWriter:

        if document.id in self.caches:
            return self.caches[document.id][1]

        blocksize = 256 * 1024

        storage = CacheBlockStorageMemory(
            blocksize=blocksize,
            total_size=document.size,
        )
        reader = CacheBlockReaderWriter(
            blocks_storage=storage,
        )

        self.caches[document.id] = (storage, reader)

        return reader


async def get_testing_channel(
    messages_source: TelegramSearch,
    documents_source: TelegramFilesSource,
) -> FsSourceTree:

    cache = DocumentsCacheFactoryMemory(blocksize=256 * 1024)
    cached_documents_source = CachingDocumentsSource(documents_source, cache)

    messages_music = await messages_source.get_messages_typed(
        "tgmounttestingchannel",
        filter=types.InputMessagesFilterMusic,  # filter=types.InputMessagesFilterDocument
    )

    messages_docs = await messages_source.get_messages_typed(
        "tgmounttestingchannel",
        filter=types.InputMessagesFilterDocument,
    )

    # zips_archives = [msg for msg in messages_docs if msg.file.name.endswith(".zip")]

    return {
        "music": {
            f"{msg.id}_{msg.file.name}": await documents_source.item_to_file_content(
                msg, msg.document
            )
            for msg in messages_music
            if msg.document is not None and msg.file is not None
        },
        "zips": z.zips_as_dirs(
            {
                f"{msg.id}_{msg.file.name}": await cached_documents_source.item_to_file_content(
                    msg, msg.document
                )
                for msg in messages_docs
                if msg.document is not None and msg.file is not None
            }
        ),
    }


async def create_sanek(
    messages_source: TelegramSearch,
    documents_source: TelegramFilesSource,
) -> FsSourceTree:
    cache = DocumentsCacheFactoryMemory(blocksize=256 * 1024)
    cached_documents_source = CachingDocumentsSource(documents_source, cache)

    music: TotalListTyped[Message] = await messages_source.get_messages_typed(
        "johnjohndoedoe",
        filter=types.InputMessagesFilterMusic,  # filter=types.InputMessagesFilterDocument
    )

    photos: TotalListTyped[Message] = await messages_source.get_messages_typed(
        "johnjohndoedoe",
        filter=types.InputMessagesFilterPhotos,
    )

    return {
        "music": {
            f"{msg.id}_{msg.file.name}": await documents_source.item_to_file_content(
                msg, msg.document
            )
            for msg in music
            if msg.document is not None and msg.file is not None
        },
        "photos": {
            f"{msg.id}_photo.jpeg": await cached_documents_source.item_to_file_content(
                msg, msg.photo
            )
            for msg in photos
            if isinstance(msg.photo, types.Photo)
        },
    }


async def mount():
    init_logging(debug=True)

    count = 10

    client = await tgclient(read_tgapp_api())

    messages_source = client
    documents_source = TelegramFilesSource(client)

    vfs_root = vfs.root(
        {
            "tgmounttestingchannel": await get_testing_channel(
                messages_source,
                documents_source,
            ),
            "sanek": await create_sanek(
                messages_source,
                documents_source,
            ),
        }
    )

    ops = fs.FileSystemOperations(vfs_root)

    await mount_ops(ops, "/home/hrn/mnt/tgmount1")


if __name__ == "__main__":
    run_main(mount)

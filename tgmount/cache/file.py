from typing import Awaitable, Callable, Optional, Protocol, TypeVar

import telethon
from tgmount.tgclient import Document
from tgmount.tgclient.files_source import get_downloadable_item

from ._factory import CacheFactoryProto
from ._storage import CacheBlockStorageMemory
from .reader import CacheBlockReaderWriter
from .types import DocId

Message = telethon.tl.custom.Message


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
    ) -> CacheBlockReaderWriter:

        item = get_downloadable_item(message)

        if item.id in self.caches:
            return self.caches[item.id][1]

        blocksize = 256 * 1024

        storage = CacheBlockStorageMemory(
            blocksize=blocksize,
            total_size=item.size,
        )
        reader = CacheBlockReaderWriter(
            blocks_storage=storage,
        )

        self.caches[item.id] = (storage, reader)

        return reader

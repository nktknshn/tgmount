from typing import Awaitable, Callable, Optional, Protocol, TypeVar

import telethon
from tgmount.cache.reader import CacheBlockReaderWriter
from tgmount.cache._storage.memory import CacheBlockStorageMemory
from .reader import CacheBlockReaderWriter
from .types import DocId


class DocumentsCacheFactory:
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

    async def cache_factory(
        self,
        message: telethon.tl.custom.Message,
        document: telethon.types.Document,
    ) -> CacheBlockReaderWriter:

        if document.id in self.caches:
            return self.caches[document.id][1]

        storage = CacheBlockStorageMemory(256 * 1024)
        reader = CacheBlockReaderWriter(
            storage,
            256 * 1024,
            document.size,
        )

        self.caches[document.id] = (storage, reader)

        return reader

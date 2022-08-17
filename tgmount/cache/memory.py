from typing import Awaitable, Callable, Optional, Protocol, TypeVar

import telethon

from ._factory import CacheFactoryProto
from ._storage import CacheBlockStorageMemory
from .reader import CacheBlockReaderWriter
from .types import DocId
from tgmount.tgclient.files_source import get_downloadable_item

Message = telethon.tl.custom.Message


class CacheFactoryMemory(CacheFactoryProto[CacheBlockReaderWriter]):
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
    ) -> CacheBlockReaderWriter:

        item = get_downloadable_item(message)

        if item.id in self._caches:
            return self._caches[item.id][1]

        blocks_storage = CacheBlockStorageMemory(
            blocksize=self._blocksize,
            total_size=item.size,
        )

        reader = CacheBlockReaderWriter(
            blocks_storage=blocks_storage,
        )

        self._caches[item.id] = (blocks_storage, reader)

        return reader

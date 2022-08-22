from typing import Type

from telethon.tl.custom import Message
from tgmount.tgclient.files_source import get_downloadable_item

from .types import (
    CacheBlockReaderWriter,
    CacheBlockReaderWriterProto,
    CacheBlocksStorage,
    CacheBlocksStorageProto,
    CacheFactoryProto,
    DocId,
)
from .util import get_bytes_count


class CacheFactory(CacheFactoryProto[CacheBlockReaderWriterProto]):
    """This class is gonna decide how to store documents cache if needed"""

    CacheBlocksStorage: Type[CacheBlocksStorage]
    CacheBlockReaderWriter: Type[CacheBlockReaderWriter]

    def __init__(self, *, block_size: int | str, capacity: int | str) -> None:
        self._capacity = get_bytes_count(capacity)
        self._blocksize = get_bytes_count(block_size)
        self._caches: dict[
            DocId, tuple[CacheBlocksStorageProto, CacheBlockReaderWriterProto]
        ] = {}

    async def total_stored(self) -> int:
        total = 0
        for k, (storage, reader) in self._caches.items():
            total += await storage.total_stored()

        return total

    async def get_cache(
        self,
        message: Message,
    ) -> CacheBlockReaderWriterProto:

        item = get_downloadable_item(message)

        if (tpl := self._caches.get(item.id)) is not None:
            return tpl[1]

        blocks_storage = self.CacheBlocksStorage(
            blocksize=self._blocksize,
            total_size=item.size,
        )

        reader = self.CacheBlockReaderWriter(
            blocks_storage=blocks_storage,
        )

        self._caches[item.id] = (blocks_storage, reader)

        return reader

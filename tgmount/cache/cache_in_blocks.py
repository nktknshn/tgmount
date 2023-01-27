import abc
from typing import Mapping, Type

from telethon.tl.custom import Message
from tgmount.cache.reader import CacheBlockReaderWriter

from tgmount.tgclient.files_source import get_filesource_item
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.tgclient.message_types import MessageProto
from .types import (
    CacheBlockReaderWriterBaseProto,
    CacheBlockReaderWriterProto,
    CacheBlocksStorageProto,
    CacheProtoGeneric,
    DocId,
)
from .util import get_bytes_count
from .logger import module_logger


class CacheBlockReaderPassby(CacheBlockReaderWriterBaseProto):
    async def read_range(self, fetcher, offset, size):
        return await fetcher(offset, size)


class CacheBlockReaderLimitedBLocks(CacheBlockReaderWriter):
    def __init__(
        self, blocks_storage: CacheBlocksStorageProto, blocks_limit: int
    ) -> None:
        super().__init__(blocks_storage)
        self._blocks_limit = blocks_limit

    async def read_range(self, fetcher, offset, size):
        block_count = len(await self._blocks_storage.blocks())

        if block_count == self._blocks_limit:
            return await fetcher(offset, size)
        else:
            return await super().read_range(fetcher, offset, size)


class CacheInBlocks(CacheProtoGeneric[CacheBlockReaderWriterProto]):
    """This class is gonna decide how to store documents cache if needed"""

    logger = module_logger.getChild("CacheInBlocks")

    CacheBlocksStorage: Type[CacheBlocksStorageProto]
    CacheBlockReaderWriter: Type[CacheBlockReaderWriterBaseProto]

    @property
    def block_size(self):
        return self._block_size

    @property
    def capacity(self):
        return self._capacity

    @property
    def documents(self):
        return list(self._caches.keys())

    @classmethod
    @abc.abstractmethod
    async def create(cls, **kwargs) -> "CacheInBlocks":
        ...

    def __init__(self, *, block_size: int | str, capacity: int | str) -> None:
        self._capacity = get_bytes_count(capacity)
        self._block_size = get_bytes_count(block_size)
        self._caches: dict[
            DocId, tuple[CacheBlocksStorageProto, CacheBlockReaderWriterProto]
        ] = {}
        self._docid_to_message: dict[DocId, MessageDownloadable] = {}

    async def total_stored(self) -> int:
        total = 0
        for k, (storage, reader) in self._caches.items():
            total += await storage.total_stored()

        return total

    async def stored_per_message(self) -> list[tuple[MessageDownloadable, int]]:
        result = []

        for doc_id, (storage, reader) in self._caches.items():
            message = self._docid_to_message[doc_id]

            result.append((message, await storage.total_stored()))

        return result

    async def create_reader(
        self, message: MessageDownloadable, blocks_storage: CacheBlocksStorageProto
    ):
        return self.CacheBlockReaderWriter(
            blocks_storage=blocks_storage,
        )

    async def create_block_storage(self, message: MessageDownloadable):
        return self.CacheBlocksStorage(
            block_size=self._block_size,
            total_size=get_filesource_item(message).size,
        )

    async def get_reader(
        self,
        message: MessageDownloadable,
    ) -> CacheBlockReaderWriterProto:

        doc_id = MessageDownloadable.document_or_photo_id(message)

        if (tpl := self._caches.get(doc_id)) is not None:
            return tpl[1]

        self._docid_to_message[doc_id] = message

        blocks_storage = await self.create_block_storage(message)
        reader = await self.create_reader(message, blocks_storage)

        self._caches[doc_id] = (blocks_storage, reader)

        return reader

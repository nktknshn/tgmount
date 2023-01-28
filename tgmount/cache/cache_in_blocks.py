import abc
from os import read
from typing import Awaitable, Callable, Mapping, Protocol, Type

from telethon.tl.custom import Message
from tgmount.cache.reader import CacheBlockReaderWriter
from tgmount.util import map_none_else, none_fallback_lazy

from tgmount.util.func import snd
from tgmount.tgclient.files_source import get_filesource_item
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.tgclient.message_types import MessageProto
from .types import (
    RangeFetcher,
    CacheBlockReaderWriterBaseProto,
    CacheBlockReaderWriterProto,
    CacheBlocksStorageProto,
    CacheProtoGeneric,
    DocId,
)
from .util import get_bytes_count
from .logger import logger


class CacheBlockReaderPassby(CacheBlockReaderWriterBaseProto):
    async def read_range(self, fetcher, offset, size):
        return await fetcher(offset, size)


class CacheBlockReaderLimitedBLocks(CacheBlockReaderWriter):
    def __init__(
        self, blocks_storage: CacheBlocksStorageProto, blocks_limit: int
    ) -> None:
        super().__init__(blocks_storage)
        self._blocks_limit = blocks_limit

    async def put_block(self, block_number: int, block: bytes):
        block_count = len(await self._blocks_storage.blocks())

        if block_count == self._blocks_limit:
            pass
        else:
            return await super().put_block(block_number, block)


class CacheBlockCapacityHandlerProto(Protocol):
    @abc.abstractmethod
    async def put_block(
        self, reader: CacheBlockReaderWriter, block_number: int, block: bytes
    ):
        pass


class CacheBlockReaderCapacityAware(CacheBlockReaderWriter):
    def __init__(
        self,
        blocks_storage: CacheBlocksStorageProto,
        capacity_handler: CacheBlockCapacityHandlerProto,
        tag=None,
    ) -> None:
        super().__init__(blocks_storage, tag=tag)
        self._capacity_handler = capacity_handler

    async def put_block(self, block_number: int, block: bytes, force=False):
        if force:
            await super().put_block(block_number, block)
            return

        await self._capacity_handler.put_block(self, block_number, block)


class CacheInBlocks(
    CacheProtoGeneric[CacheBlockReaderWriterProto],
    CacheBlockCapacityHandlerProto,
):
    """This class is gonna decide how to store documents cache if needed"""

    logger = logger.getChild("CacheInBlocks")

    CacheBlocksStorage: Type[CacheBlocksStorageProto]

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
            DocId, tuple[CacheBlocksStorageProto, CacheBlockReaderCapacityAware]
        ] = {}
        self._docid_to_message: dict[DocId, MessageDownloadable] = {}
        self._by_reader: dict[
            CacheBlockReaderCapacityAware, tuple[CacheBlocksStorageProto, DocId]
        ] = {}

    @property
    def readers(self) -> list[CacheBlockReaderCapacityAware]:
        return list(map(snd, self._caches.values()))

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
        return CacheBlockReaderCapacityAware(
            blocks_storage=blocks_storage,
            capacity_handler=self,
            tag=message.file.name,
        )

    async def create_block_storage(self, message: MessageDownloadable):
        return self.CacheBlocksStorage(
            block_size=self._block_size,
            total_size=get_filesource_item(message).size,
        )

    async def put_block(
        self, reader: CacheBlockReaderWriterProto, block_number: int, block: bytes
    ):
        if reader not in self._by_reader:
            self.logger.error(f"put_block: Missing {reader}.")
            return

        total_stored = await self.total_stored()

        if total_stored + self.block_size > self.capacity:
            await self.discard_useless_blocks()

        await reader.put_block(block_number, block, force=True)

    @property
    def sorted_readers_by_read_time(self):
        return list(
            sorted(
                self.readers,
                key=lambda r: map_none_else(
                    r.last_read_time, lambda t: t.timestamp(), 0
                ),
            )
        )

    async def discard_useless_blocks(
        self,
    ):
        readers = self.sorted_readers_by_read_time

        if len(readers) == 0:
            self.logger.debug(f"No readers.")
            return

        for reader in readers:
            if await reader.blocks_storage.total_stored() == 0:
                continue

            (storage, doc_id) = self._by_reader[reader]
            message = self._docid_to_message[doc_id]

            self.logger.debug(f"Discarding block from {message.file.name}.")
            await reader.discard_least_read_block()
            break

        # self.logger.debug(f"Total stored {await self.total_stored()}.")

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
        self._by_reader[reader] = (blocks_storage, doc_id)

        return reader

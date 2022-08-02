import logging
from typing import Awaitable, Callable, Generic, Optional, Protocol, Set, TypeVar

from ._storage.types import CacheBlocksStorageProto

BlockFetcher = Callable[[int, int], Awaitable[bytes]]

logger = logging.getLogger("tgmount-cache")


class CacheBlockReaderWriterProto(Protocol):
    async def read_range(self, fetcher: BlockFetcher, offset: int, size: int):
        raise NotImplementedError()


class CacheBlockReaderWriter:
    def __init__(self, blocks_storage: CacheBlocksStorageProto) -> None:
        self._blocks_storage: CacheBlocksStorageProto = blocks_storage
        self._blocks_read_count: dict[int, int] = {}

    def range_blocks(self, offset: int, limit: int):
        """Get block ids for the range"""

        start = offset
        end = offset + limit

        start_block_number = start // self._blocks_storage.blocksize
        end_block_number = end // self._blocks_storage.blocksize

        return list(range(start_block_number, end_block_number + 1))

    async def has_range(self, offset: int, limit: int):
        """Returns if storage has the range cached"""

        return (
            set(self.range_blocks(offset, limit)) <= await self._blocks_storage.blocks()
        )

    async def try_read_range(self, offset: int, limit: int):
        """Returns None if the cache doesn't have required blocks"""

        start = offset
        start_pos = start % self._blocks_storage.blocksize
        result = b""

        for block_number in self.range_blocks(offset, limit):
            if block := await self._blocks_storage.get(block_number):
                result += block
            else:
                return None

        return result[start_pos : start_pos + limit]

    async def read_range(self, block_fetcher: BlockFetcher, offset: int, limit: int):
        """Returns bytes for the range fetching and storing missing blocks"""

        start = offset
        end = offset + limit

        start_pos = start % self._blocks_storage.blocksize
        end_pos = end % self._blocks_storage.blocksize

        result = b""

        for block_number in self.range_blocks(offset, limit):
            if block := await self._blocks_storage.get(block_number):
                logger.debug(
                    f"CacheBlockReaderWriter.read_range({offset}, {limit} ({limit//1024} kb)): block {block_number} hit"
                )
            else:
                logger.debug(
                    f"CacheBlockReaderWriter.read_range({offset}, {limit} ({limit//1024} kb)): block {block_number} miss"
                )
                block = await block_fetcher(
                    block_number * self._blocks_storage.blocksize,
                    self._blocks_storage.blocksize,
                )

                await self._blocks_storage.put(block_number, block)
            result += block

        return result[start_pos : start_pos + limit]

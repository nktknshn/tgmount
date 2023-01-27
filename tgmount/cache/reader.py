from collections import defaultdict
from datetime import datetime
import logging
from tgmount.util.func import snd
from .types import (
    RangeFetcher,
    CacheBlocksStorageProto,
    CacheBlockReaderWriterBaseProto,
)

from .logger import logger


class CacheBlockReaderWriter(CacheBlockReaderWriterBaseProto):
    """Reads blocks from a block storage and writes to"""

    logger = logger.getChild("CacheBlockReaderWriter")

    def __init__(self, blocks_storage: CacheBlocksStorageProto) -> None:
        self._blocks_storage: CacheBlocksStorageProto = blocks_storage
        self._blocks_read_count: defaultdict[int, int] = defaultdict(lambda: 0)
        self._last_read_time: datetime | None = None

    @property
    def blocks_storage(self):
        return self._blocks_storage

    @property
    def last_read_time(self) -> datetime | None:
        return self._last_read_time

    async def discard_least_read_block(self):
        s = list(sorted(self._blocks_read_count.items(), key=snd))

        if len(s) == 0:
            self.logger.debug(f"Nothing to discard.")
            return

        block_id = s[0][0]

        self.logger.debug(f"Discarding block {block_id}")

        del self._blocks_read_count[block_id]
        await self._blocks_storage.discard_blocks({block_id})

    def range_blocks(self, offset: int, limit: int):
        """Get block ids for the range"""

        start = offset
        end = offset + limit

        start_block_number = start // self._blocks_storage.block_size
        end_block_number = end // self._blocks_storage.block_size

        return list(range(start_block_number, end_block_number + 1))

    async def has_range(self, offset: int, limit: int):
        """Returns if storage has the range cached"""

        return (
            set(self.range_blocks(offset, limit)) <= await self._blocks_storage.blocks()
        )

    async def try_read_range(self, offset: int, limit: int):
        """Returns None if the cache doesn't have required blocks"""

        start = offset
        start_pos = start % self._blocks_storage.block_size
        result = b""

        for block_number in self.range_blocks(offset, limit):
            if block := await self._blocks_storage.get(block_number):
                result += block
            else:
                return None

        return result[start_pos : start_pos + limit]

    async def fetch_block(self, range_fetcher: RangeFetcher, block_number: int):
        return await range_fetcher(
            block_number * self._blocks_storage.block_size,
            self._blocks_storage.block_size,
        )

    async def get_block(self, block_number: int) -> bytes | None:
        return await self._blocks_storage.get(block_number)

    async def put_block(self, block_number: int, block: bytes):
        await self._blocks_storage.put(block_number, block)

    async def read_range(self, range_fetcher: RangeFetcher, offset: int, limit: int):
        """Returns bytes for the range fetching and storing missing blocks"""

        start = offset
        end = offset + limit

        start_pos = start % self._blocks_storage.block_size
        end_pos = end % self._blocks_storage.block_size

        result = b""

        for block_number in self.range_blocks(offset, limit):
            if block := await self.get_block(block_number):
                self.logger.debug(
                    f"read_range(offset={offset}, limit={limit} ({limit//1024} kb)): block {block_number} hit"
                )
            else:
                self.logger.debug(
                    f"read_range({offset}, {limit} ({limit//1024} kb)): block {block_number} miss"
                )

                block = await self.fetch_block(range_fetcher, block_number)

                await self.put_block(block_number, block)

            self._blocks_read_count[block_number] += 1

            result += block

        self._last_read_time = datetime.now()
        return result[start_pos : start_pos + limit]

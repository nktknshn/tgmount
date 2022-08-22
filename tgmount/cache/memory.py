from typing import Awaitable, Callable, Optional, Protocol, TypeVar

import telethon

from .factory import CacheFactory
from .reader import CacheBlockReaderWriter
from .types import CacheBlocksStorage

Message = telethon.tl.custom.Message


class CacheBlocksStorageMemory(CacheBlocksStorage):
    def __init__(self, blocksize: int, total_size: int):
        self._blocksize = blocksize
        self._total_size = total_size
        self._blocks: dict[int, bytes] = {}

    @property
    def blocksize(self):
        return self._blocksize

    @property
    def total_size(self):
        return self._total_size

    async def get(self, block_number: int) -> Optional[bytes]:
        return self._blocks.get(block_number)

    async def put(self, block_number: int, block: bytes):
        self._blocks[block_number] = block

    async def blocks(self):
        return set(self._blocks.keys())

    async def total_stored(self):
        return len(await self.blocks()) * self.blocksize


class CacheFactoryMemory(CacheFactory):
    """This class is gonna decide how to store documents cache if needed"""

    CacheBlocksStorage = CacheBlocksStorageMemory
    CacheBlockReaderWriter = CacheBlockReaderWriter

    def __init__(self, *, block_size: int | str, capacity: int | str) -> None:
        super().__init__(block_size=block_size, capacity=capacity)

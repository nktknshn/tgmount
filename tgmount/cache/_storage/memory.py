from typing import Optional
from .types import CacheBlocksStorageProto


class CacheBlockStorageMemory(CacheBlocksStorageProto):
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
from typing import Optional


from .cache_in_blocks import CacheInBlocks
from .reader import CacheBlockReaderWriter
from .types import CacheBlocksStorageProto
from .logger import module_logger


class CacheBlocksStorageMemory(CacheBlocksStorageProto):
    """Storage for blocks of a single file"""

    logger = module_logger.getChild(f"CacheBlocksStorageMemory")

    def __init__(self, block_size: int, total_size: int):
        self._block_size = block_size
        self._total_size = total_size
        self._blocks: dict[int, bytes] = {}

    async def discard_blocks(self, blocks: set[int]) -> None:
        for b in blocks:
            if b in self._blocks:
                del self._blocks[b]
            else:
                self.logger.warning(
                    f"discard_blocks: Missing block {b} in the storage."
                )

    @property
    def block_size(self):
        return self._block_size

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
        return len(await self.blocks()) * self.block_size


class CacheMemory(CacheInBlocks):
    """This class is gonna decide how to store documents cache if needed"""

    CacheBlocksStorage = CacheBlocksStorageMemory
    CacheBlockReaderWriter = CacheBlockReaderWriter

    def __init__(
        self,
        *,
        block_size: int | str,
        capacity: int | str,
    ) -> None:
        super().__init__(block_size=block_size, capacity=capacity)

    @classmethod
    async def create(cls, *, block_size: int | str, capacity: int | str):
        return CacheMemory(block_size=block_size, capacity=capacity)

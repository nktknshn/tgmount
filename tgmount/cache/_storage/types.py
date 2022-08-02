from typing import Awaitable, Callable, Generic, Optional, Protocol, Set, TypeVar


class CacheBlocksStorageProto(Protocol):
    blocksize: int
    total_size: int

    async def total_stored(self) -> int:
        raise NotImplementedError()

    async def get(self, block_number: int) -> Optional[bytes]:
        raise NotImplementedError()

    async def put(self, block_number: int, block: bytes):
        raise NotImplementedError()

    async def blocks(self) -> Set[int]:
        raise NotImplementedError()

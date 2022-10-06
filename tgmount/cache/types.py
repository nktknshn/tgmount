from abc import abstractmethod
from typing import (
    Awaitable,
    Callable,
    Generic,
    Optional,
    Protocol,
    Set,
    TypeVar,
)

import telethon

T = TypeVar("T", covariant=True)

DocId = int

BlockFetcher = Callable[[int, int], Awaitable[bytes]]


class CacheBlockReaderWriterProto(Protocol):
    async def read_range(self, fetcher: BlockFetcher, offset: int, size: int):
        raise NotImplementedError()


class CacheBlocksStorageProto(Protocol):
    blocksize: int
    total_size: int

    @abstractmethod
    def __init__(self, blocksize: int, total_size: int) -> None:
        pass

    @abstractmethod
    async def total_stored(self) -> int:
        ...

    @abstractmethod
    async def get(self, block_number: int) -> Optional[bytes]:
        ...

    @abstractmethod
    async def put(self, block_number: int, block: bytes):
        ...

    @abstractmethod
    async def blocks(self) -> Set[int]:
        ...

    # async def discard_blocks(self, blocks: set[int]) -> None:
    #     raise NotImplementedError()


class CacheFactoryProto(Protocol, Generic[T]):
    @abstractmethod
    def __init__(self, **kwargs) -> None:
        ...

    @abstractmethod
    async def total_stored(self) -> int:
        ...

    @abstractmethod
    async def get_cache(
        self,
        message: telethon.tl.custom.Message,
    ) -> T:
        ...


class CachingDocumentsStorageError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class CacheFactory(CacheFactoryProto[CacheBlockReaderWriterProto], Protocol):
    pass


class CacheBlockReaderWriter(CacheBlockReaderWriterProto):
    @abstractmethod
    def __init__(self, blocks_storage: CacheBlocksStorageProto) -> None:
        pass

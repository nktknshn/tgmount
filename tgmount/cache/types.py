from abc import abstractmethod
from typing import (
    AnyStr,
    Awaitable,
    Callable,
    Generic,
    List,
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

    async def total_stored(self) -> int:
        raise NotImplementedError()

    async def get(self, block_number: int) -> Optional[bytes]:
        raise NotImplementedError()

    async def put(self, block_number: int, block: bytes):
        raise NotImplementedError()

    async def blocks(self) -> Set[int]:
        raise NotImplementedError()

    # async def discard_blocks(self, blocks: set[int]) -> None:
    #     raise NotImplementedError()


class CacheBlocksStorage(CacheBlocksStorageProto):
    blocksize: int
    total_size: int

    @abstractmethod
    def __init__(self, blocksize: int, total_size: int) -> None:
        pass


class CacheFactoryProto(Protocol, Generic[T]):
    async def get_cache(
        self,
        message: telethon.tl.custom.Message,
    ) -> T:
        raise NotImplementedError()


class CachingDocumentsStorageError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class CacheFactory(CacheFactoryProto[CacheBlockReaderWriterProto]):
    @abstractmethod
    def __init__(self, **kwargs) -> None:
        pass


class CacheBlockReaderWriter(CacheBlockReaderWriterProto):
    @abstractmethod
    def __init__(self, blocks_storage: CacheBlocksStorage) -> None:
        pass

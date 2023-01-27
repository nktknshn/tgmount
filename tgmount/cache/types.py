from abc import abstractclassmethod, abstractmethod
from typing import (
    Awaitable,
    Callable,
    Generic,
    Mapping,
    Optional,
    Protocol,
    Set,
    TypeVar,
)

import telethon

from tgmount.tgclient.message_types import MessageProto
from tgmount.tgmount.file_factory.types import FileFactoryProto

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


class CacheProtoGeneric(Protocol, Generic[T]):
    @abstractclassmethod
    async def create(cls, **kwargs) -> "CacheProtoGeneric[T]":
        ...

    @abstractmethod
    async def total_stored(self) -> int:
        ...

    @abstractmethod
    async def get_reader(
        self,
        message: MessageProto,
    ) -> T:
        ...


class CachingDocumentsStorageError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class CacheProto(CacheProtoGeneric[CacheBlockReaderWriterProto], Protocol):
    pass


class CacheBlockReaderWriterBase(CacheBlockReaderWriterProto):
    @abstractmethod
    def __init__(self, blocks_storage: CacheBlocksStorageProto) -> None:
        pass

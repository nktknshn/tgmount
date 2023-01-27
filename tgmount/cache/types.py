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
from typing_extensions import Self

import telethon
from tgmount.tgclient.guards import MessageDownloadable

from tgmount.tgclient.message_types import MessageProto
from tgmount.tgmount.file_factory.types import FileFactoryProto

T = TypeVar("T", covariant=True)

DocId = int

RangeFetcher = Callable[[int, int], Awaitable[bytes]]


class CacheBlockReaderWriterProto(Protocol):
    async def read_range(self, fetcher: RangeFetcher, offset: int, size: int):
        raise NotImplementedError()


class CacheBlocksStorageProto(Protocol):
    """Storage for blocks of a single file"""

    block_size: int
    total_size: int

    @abstractmethod
    def __init__(self, block_size: int, total_size: int) -> None:
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

    @abstractmethod
    async def discard_blocks(self, blocks: set[int]) -> None:
        ...

    # async def discard_blocks(self, blocks: set[int]) -> None:
    #     raise NotImplementedError()


class CacheProtoGeneric(Protocol, Generic[T]):
    @abstractclassmethod
    async def create(cls, **kwargs) -> Self:
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


class CacheInBlocksProto(CacheProtoGeneric[CacheBlockReaderWriterProto], Protocol):
    block_size: int
    capacity: int
    documents: list[DocId]

    @abstractmethod
    async def stored_per_message(self) -> list[tuple[MessageDownloadable, int]]:
        ...


class CacheBlockReaderWriterBaseProto(CacheBlockReaderWriterProto):
    @abstractmethod
    def __init__(self, blocks_storage: CacheBlocksStorageProto) -> None:
        pass

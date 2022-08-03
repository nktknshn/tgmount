import time
from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    ByteString,
    Callable,
    Generic,
    Iterable,
    List,
    Optional,
    Protocol,
    TypeGuard,
    TypeVar,
    Union,
)

from datetime import datetime


@dataclass
class FileLike:
    name: str
    content: "FileContentProto"

    creation_time: datetime = datetime.now()

    def __str__(self):
        return f"FileLike({self.name})"

    @property
    def is_directory(self):
        return False

    @staticmethod
    def guard(item: Any) -> TypeGuard["FileLike"]:
        return isinstance(item, FileLike)


T = TypeVar("T")


class FileContentProto(Protocol, Generic[T]):
    """
    Abstract source of data
    """

    size: int

    async def open_func(self) -> T:
        raise NotImplementedError()

    async def read_func(self, handle: T, off: int, size: int) -> bytes:
        raise NotImplementedError()

    async def close_func(self, handle: T):
        raise NotImplementedError()

    async def seek_func(self, handle: T, n: int, w: int):
        raise NotImplementedError()

    async def tell_func(self, handle: T):
        raise NotImplementedError()

    @staticmethod
    def guard(item: Any) -> TypeGuard["FileContentProto"]:
        return hasattr(item, "read_func")


async def async_noop(*args):
    pass


def async_constant(v):
    async def _inner(*args):
        return v

    return _inner


@dataclass
class FileContent(FileContentProto):
    size: int

    read_func: Callable[[Any, int, int], Awaitable[bytes]]
    open_func: Callable[[], Awaitable[Any]] = async_noop
    close_func: Callable[[Any], Awaitable[None]] = async_noop
    seek_func: Callable[[Any, int, int], Awaitable[Any]] = async_noop

    # XXX
    tell_func: Optional[Callable[[Any], Awaitable[int]]] = None


@dataclass
class FileContentHandle:
    file_content: FileContentProto
    handle: Any
    is_closed: bool = False

    async def read(self, off: int, size: int) -> bytes:
        return await self.file_content.read_func(self.handle, off, size)

    async def close(self):
        await self.file_content.close_func(self.handle)
        self.is_closed = True

    async def seek(self, n: int, w: int):
        return await self.file_content.seek_func(self.handle, n, w)

    async def tell(self):
        return await self.file_content.tell_func(self.handle)

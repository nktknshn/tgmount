from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    Protocol,
    TypeGuard,
    TypeVar,
)


@dataclass
class FileLike:
    name: str
    content: "FileContentProto"

    creation_time: datetime = datetime.now()

    extra: Optional[Any] = None
    """ Any extra data attached to the FileLike  """

    @staticmethod
    def guard(item: Any) -> TypeGuard["FileLike"]:
        return isinstance(item, FileLike)

    def __repr__(self) -> str:
        return f"FileLike({self.name}, {self.content})"


T = TypeVar("T")


class FileContentProto(Protocol, Generic[T]):
    """
    Abstract source of file content
    """

    size: int

    @abstractmethod
    async def open_func(self) -> T:
        ...

    @abstractmethod
    async def read_func(self, handle: T, off: int, size: int) -> bytes:
        ...

    @abstractmethod
    async def close_func(self, handle: T):
        ...

    @abstractmethod
    async def seek_func(self, handle: T, n: int, w: int):
        ...

    tell_func: Optional[Callable[[Any], Awaitable[int]]] = None

    @staticmethod
    def guard(item: Any) -> TypeGuard["FileContentProto"]:
        return hasattr(item, "read_func")


async def async_noop(*args):
    pass


def async_constant(v):
    async def _inner(*args):
        return v

    return _inner


class FileContentBasic(FileContentProto):
    size: int
    encoding = "utf-8"

    @abstractmethod
    async def read(self, handle) -> str:
        pass

    async def read_func(self, handle, off: int, size: int) -> bytes:
        content = await self.read(handle)

        return content.encode(self.encoding)[off : off + size]

    async def open_func(self) -> None:
        return

    async def close_func(self, handle):
        return

    async def seek_func(self, handle, n: int, w: int):
        raise NotImplementedError()

    tell_func: Optional[Callable[[Any], Awaitable[int]]] = None


# @dataclass
class FileContent(FileContentProto):
    """implementation of `FileContentProto` with functions"""

    def __init__(
        self,
        size: int,
        read_func: Callable[[Any, int, int], Awaitable[bytes]],
        open_func: Callable[[], Awaitable[Any]] = async_noop,
        close_func: Callable[[Any], Awaitable[None]] = async_noop,
        seek_func: Callable[[Any, int, int], Awaitable[Any]] = async_noop,
        tell_func: Optional[Callable[[Any], Awaitable[int]]] = None,
    ) -> None:
        self.size = size
        self._read_func = read_func
        self._open_func = open_func
        self._close_func = close_func
        self._seek_func = seek_func

        self.tell_func = tell_func

    async def read_func(self, handle, off: int, size: int) -> bytes:
        return await self._read_func(handle, off, size)

    async def open_func(self) -> None:
        return await self._open_func()

    async def close_func(self, handle):
        return await self._close_func(handle)

    async def seek_func(self, handle, n: int, w: int):
        return await self._seek_func(handle, n, w)

    # async def tell_func(self, handle):
    #     return await self._tell_func(handle)

    # XXX

    def __repr__(self):
        return f"FileContent(size={self.size})"

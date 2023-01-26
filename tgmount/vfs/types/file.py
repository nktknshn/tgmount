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
    """implementation of `FileContentProto` with functions"""

    size: int

    read_func: Callable[[Any, int, int], Awaitable[bytes]]
    open_func: Callable[[], Awaitable[Any]] = async_noop
    close_func: Callable[[Any], Awaitable[None]] = async_noop
    seek_func: Callable[[Any, int, int], Awaitable[Any]] = async_noop

    # XXX
    tell_func: Optional[Callable[[Any], Awaitable[int]]] = None

    def __repr__(self):
        return f"FileContent(size={self.size})"

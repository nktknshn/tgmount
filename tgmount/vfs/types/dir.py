from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterable,
    Optional,
    Protocol,
    TypeGuard,
    TypeVar,
    Union,
)

from tgmount.vfs.types.file import FileLike

T = TypeVar("T")

DirContentItem = Union["DirLike", FileLike]


OpenDirFunc = Callable[[], Awaitable[Any]]
ReleaseDirFunc = Callable[[T], Awaitable[Any]]


# def is_directory(item: DirContentItem) -> TypeGuard["DirLike"]:
#     return item.is_directory


@dataclass
class DirLike:
    """Represents a folder with a name and content"""

    name: str
    content: "DirContentProto"

    creation_time: datetime = datetime.now()

    # @property
    # def is_directory(self):
    #     return True

    @staticmethod
    def guard(item: Any) -> TypeGuard["DirLike"]:
        return isinstance(item, DirLike)


class DirContentProto(Protocol[T]):
    """
    Main interface describing a content of a folder. Intended to be stateless, storing the state in
    the handle returned by `opendir_func`
    """

    @abstractmethod
    async def readdir_func(self, handle: T, off: int) -> Iterable[DirContentItem]:
        ...

    @abstractmethod
    async def opendir_func(self) -> T:
        ...

    @abstractmethod
    async def releasedir_func(self, handle: T):
        ...

    @staticmethod
    def guard(item: Any) -> TypeGuard["DirContentProto[Any]"]:
        return hasattr(item, "readdir_func")


class DirContent(DirContentProto[T]):
    """implements `DirContentProto` with functions"""

    def __init__(
        self,
        readdir_func,
        releasedir_func=None,
        opendir_func=None,
    ):
        self._readdir_func = readdir_func
        self._releasedir_func: Optional[ReleaseDirFunc[T]] = releasedir_func
        self._opendir_func: Optional[OpenDirFunc] = opendir_func

    async def readdir_func(self, handle: T, off: int) -> Iterable[DirContentItem]:
        return await self._readdir_func(handle, off)

    async def opendir_func(self):
        if self._opendir_func:
            return await self._opendir_func()

    async def releasedir_func(self, handle: T):
        if self._releasedir_func:
            return await self._releasedir_func(handle)


class DirContentList(DirContentProto[list[DirContentItem]]):
    """Immutable dir content sourced from a list of `DirContentItem`"""

    def __init__(self, content_list: list[DirContentItem]):
        self.content_list = content_list

    async def opendir_func(self) -> list[DirContentItem]:
        return self.content_list[:]

    async def releasedir_func(self, handle: list[DirContentItem]):
        return

    async def readdir_func(
        self, handle: list[DirContentItem], off: int
    ) -> Iterable[DirContentItem]:
        return handle[off:]

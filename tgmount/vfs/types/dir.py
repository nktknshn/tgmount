from typing import (
    Generic,
    Optional,
    Protocol,
    TypeGuard,
    TypeVar,
    Union,
    Callable,
    Iterable,
    List,
    Any,
    Awaitable,
)

import time
from dataclasses import dataclass

from tgmount.vfs.types.file import FileLike

DirContentItem = Union["DirLike", FileLike]


def is_directory(item: DirContentItem) -> TypeGuard["DirLike"]:
    return item.is_directory


@dataclass
class DirLike:
    name: str
    content: "DirContentProto"

    creation_time = time.time_ns()

    @property
    def is_directory(self):
        return True

    @staticmethod
    def guard(item: Any) -> TypeGuard["DirLike"]:
        return isinstance(item, DirLike)


T = TypeVar("T")

# XXX make handle type generic?


class DirContentProto(Protocol, Generic[T]):
    """
    intended to be stateless
    lazy
    """

    async def readdir_func(self, handle: T, off: int) -> Iterable[DirContentItem]:
        raise NotImplementedError()

    async def opendir_func(self) -> T:
        raise NotImplementedError()

    async def releasedir_func(self, handle: T):
        raise NotImplementedError()

    @staticmethod
    def guard(item: Any) -> TypeGuard["DirContentProto"]:
        return hasattr(item, "readdir_func")


class DirContentList(DirContentProto):
    def __init__(self, content_list: List["DirContentItem"]):
        self.content_list = content_list

    async def opendir_func(self) -> Any:
        pass

    async def releasedir_func(self, handle: Any):
        pass

    async def readdir_func(self, handle, off: int) -> Iterable[DirContentItem]:
        return self.content_list[off:]


class DirContentListUpdatable(DirContentProto):
    def __init__(self, content_list: List["DirContentItem"]):
        self.content_list = content_list

    def on_update(self, new_item: DirContentItem):
        self.content_list.append(new_item)

    async def opendir_func(self) -> Any:
        pass

    async def releasedir_func(self, handle: Any):
        pass

    async def readdir_func(self, handle, off: int) -> Iterable[DirContentItem]:
        return self.content_list[off:]

    def __repr__(self):
        return f"DirListUpdatable({str(self.content_list)})"


# @dataclass
# class OpendirContext:
#     full_path: Optional[str] = None
#     vfs_path: Optional[str] = None

OpenDirFunc = Callable[[], Awaitable[Any]]
# OpenDirFunc = Callable[[Optional[OpendirContext]], Awaitable[Any]]


class DirContent(DirContentProto):
    def __init__(self, readdir_func, releasedir_func=None, opendir_func=None):
        self._readdir_func = readdir_func
        self._releasedir_func = releasedir_func
        self._opendir_func: Optional[OpenDirFunc] = opendir_func

    async def readdir_func(self, handle, off: int) -> Iterable[DirContentItem]:
        return await self._readdir_func(off)

    async def opendir_func(self):
        if self._opendir_func:
            return await self._opendir_func()

    async def releasedir_func(self, handle):
        if self._releasedir_func:
            return await self._releasedir_func()

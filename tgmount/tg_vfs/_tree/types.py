from dataclasses import dataclass, field, replace
from typing import Callable, Generic, Mapping, Protocol, TypeGuard, TypeVar, Union, cast

from tgmount import vfs
from tgmount.tgclient.search.filtering.guards import *

from telethon.tl.custom import Message


_T = TypeVar("_T")

MessagesTreeValueDir = Union[
    Iterable[_T],
    Iterable["Virt.Dir[_T]"],
    Iterable["Virt.Dir[_T]" | _T],
    "Virt.MapContent[_T]",
    "Virt.MapContext[_T]",
    # _T,
]


# MessagesTreeValue = Union[
#     _T,
#     MessagesTreeValueDirContent[_T],
# ]

MessagesTreeValue = MessagesTreeValueDir[_T]

# MessagesTreeValue is what a value of tree may be
MessagesTree = vfs.DirTree[
    MessagesTreeValue[_T],
]


@dataclass
class WalkTreeContext:
    path: list[str | int] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def push_path(self, element: str | int) -> "WalkTreeContext":
        return replace(self, path=[*self.path, element])

    def put_extra(self, key: str, value) -> "WalkTreeContext":
        return replace(self, extra={**self.extra, key: value})


class Virt:
    @dataclass
    class Dir(Generic[_T]):
        name: str
        content: MessagesTree | MessagesTreeValueDir[_T]

    @dataclass
    class File(Generic[_T]):
        name: str
        content: _T

    @dataclass
    class MapContent(Generic[_T]):
        mapper: Callable[[vfs.DirContentProto], vfs.DirContentProto]
        content: MessagesTreeValueDir[_T]

    @dataclass
    class MapContext(Generic[_T]):
        mapper: Callable[[WalkTreeContext], WalkTreeContext]
        tree: MessagesTree | MessagesTreeValue


class MessagesTreeHandlerProto(Protocol[_T]):
    def fstree(self, tree: MessagesTree[_T]) -> vfs.FsSourceTree:
        ...

    def dir_or_file_content(self, message: _T) -> vfs.DirContent | vfs.FileContent:
        ...

    def supports(self, message: Message) -> TypeGuard[_T]:
        ...

    def dir_or_file(self, message: _T) -> vfs.DirLike | vfs.FileLike:
        ...

    def dir_content(self, message: _T) -> vfs.DirContentProto:
        ...

    def from_dir_like(self, dl: Virt.Dir[_T]) -> vfs.DirContentProto:
        ...

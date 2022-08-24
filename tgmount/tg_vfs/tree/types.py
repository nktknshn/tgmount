from dataclasses import dataclass, field, replace
from typing import Callable, Generic, Mapping, Protocol, TypeGuard, TypeVar, Union, cast

from tgmount import vfs
from tgmount.tgclient.guards import *

from telethon.tl.custom import Message
from tgmount.vfs.map_tree import MapTreeContext

_T = TypeVar("_T")

""" Type that can be an item of Iterable """
MessagesTreeValueDirItem = Union[
    _T,
    "Virt.Dir[_T]",
    "Virt.Dir[_T]" | _T,
    vfs.DirLike,
    vfs.FileLike,
]

""" Type the can be turned into DirContent """
MessagesTreeValueDir = Union[
    Iterable[MessagesTreeValueDirItem[_T]],
    "Virt.MapContent[_T]",
    "Virt.MapContext[_T]",
    vfs.DirContentProto,
    Mapping[str, "MessagesTreeValueDir[_T] | vfs.FileContentProto"]
    # vfs.FileContentProto
    # _T,
]

""" Type that can be a value of `MessagesTree` Mapping (file content or dir content)"""
MessagesTreeValue = Union[
    MessagesTreeValueDir[_T],
    vfs.FileContentProto
    # _T,
]

""" 
MessagesTreeValue is what a value of tree may be
MessagesTreeValue is a structure that can be turned into DirContentProto
It is either MessagesTreeValueDir or Mapping of item names into content (which may be
DirContent of FileContent
)
"""
MessagesTree = (
    MessagesTreeValueDir[T] | Mapping[str, "MessagesTree[T]" | MessagesTreeValue[T]]
)
# MessagesTree = vfs.Tree[
#     MessagesTreeValue[_T],
# ]


class Virt:
    @dataclass
    class Dir(Generic[_T]):
        name: str
        content: MessagesTree[_T]

    @dataclass
    class File(Generic[_T]):
        name: str
        content: _T

    @dataclass
    class MapContent(Generic[_T]):
        mapper: Callable[[vfs.DirContentProto], vfs.DirContentProto]
        content: MessagesTree[_T]

    @dataclass
    class MapContext(Generic[_T]):
        mapper: Callable[[MapTreeContext], MapTreeContext]
        tree: MessagesTree[_T]

    # @dataclass
    # class WithContext(Generic[_T]):
    #     mapper: Callable[[WalkTreeContext], MessagesTreeValue[_T]]
    #     tree: MessagesTreeValue[_T]

    # @dataclass
    # class MapTree(Generic[_T]):
    #     mapper: Callable[
    #         [WalkTreeContext, MessagesTreeValue[_T]], MessagesTreeValue[_T]
    #     ]

from dataclasses import dataclass, field, replace
from typing import Callable, Generic, Mapping, Protocol, TypeGuard, TypeVar, Union, cast

from tgmount import vfs
from tgmount.tgclient.guards import *

from telethon.tl.custom import Message
from tgmount.vfs.map_tree import MapTreeContext

T = TypeVar("T")

""" Type that can be an item of Iterable """
MessagesTreeValueDirItem = Union[
    T,
    "Virt.Dir[T]",
    vfs.DirLike,
    vfs.FileLike,
]

""" Type that the can be turned into DirContentProto """
MessagesTreeValueDir = Union[
    Iterable[MessagesTreeValueDirItem[T]],
    "Virt.MapContent[T]",
    "Virt.MapContext[T]",
    vfs.DirContentProto,
    Mapping[str, "MessagesTree[T] | MessagesTreeValue[T]"],
]

""" Type that can be a value of `MessagesTree` Mapping (file content or dir content)"""
MessagesTreeValue = Union[
    MessagesTreeValueDir[T],
    vfs.FileContentProto,
]

""" 
MessagesTree is a structure that can be turned into DirContentProto
It is either MessagesTreeValueDir or Mapping of item names into conten
(which may be DirContent of FileContent)
"""
MessagesTree = (
    MessagesTreeValueDir[T]
    # | Mapping[str, "MessagesTree[T]" | MessagesTreeValue[T]]
)
# MessagesTree = vfs.Tree[
#     MessagesTreeValue[_T],
# ]


class Virt:
    @dataclass
    class Dir(Generic[T]):
        name: str
        content: MessagesTree[T]

    # @dataclass
    # class File(Generic[T]):
    #     name: str
    #     content: T

    @dataclass
    class MapContent(Generic[T]):
        mapper: Callable[[vfs.DirContentProto], vfs.DirContentProto]
        content: MessagesTree[T]

    @dataclass
    class MapContext(Generic[T]):
        mapper: Callable[[MapTreeContext], MapTreeContext]
        tree: MessagesTree[T]

    # @dataclass
    # class WithContext(Generic[_T]):
    #     mapper: Callable[[WalkTreeContext], MessagesTreeValue[_T]]
    #     tree: MessagesTreeValue[_T]

    # @dataclass
    # class MapTree(Generic[_T]):
    #     mapper: Callable[
    #         [WalkTreeContext, MessagesTreeValue[_T]], MessagesTreeValue[_T]
    #     ]

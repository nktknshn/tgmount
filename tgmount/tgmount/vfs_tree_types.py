from abc import abstractclassmethod, abstractmethod
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, Union

from tgmount import vfs

T = TypeVar("T")


class VfsTreeProto(Protocol):
    pass


@dataclass
class TreeEventRemovedItems(Generic[T]):
    """Triggered by `VfsTree.remove_content`"""

    sender: T
    update_path: str
    removed_items: list[vfs.DirContentItem]


@dataclass
class TreeEventNewItems(Generic[T]):
    """Triggered by `VfsTree.put_content`"""

    sender: T
    update_path: str
    new_items: list[vfs.DirContentItem]


@dataclass
class TreeEventRemovedDirs(Generic[T]):
    """Triggered by `VfsTree.remove_dir`"""

    sender: T
    update_path: str
    removed_dirs: list[str]


@dataclass
class TreeEventNewDirs(Generic[T]):
    """Triggered by `VfsTree.put_dir` and `VfsTree.create_dir`"""

    sender: T
    update_path: str
    new_dirs: list[str]


TreeEventType = (
    TreeEventRemovedItems[T]
    | TreeEventNewItems[T]
    | TreeEventRemovedDirs[T]
    | TreeEventNewDirs[T]
)

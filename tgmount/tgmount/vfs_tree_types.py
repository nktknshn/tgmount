from abc import abstractclassmethod, abstractmethod
from dataclasses import dataclass
from typing import Generic, Mapping, Protocol, TypeVar, Union

from tgmount import vfs

T = TypeVar("T")


class VfsTreeProto(Protocol):
    pass


@dataclass
class TreeEventRemovedItems(Generic[T]):
    """Triggered by `VfsTree.remove_content`"""

    sender: T
    removed_items: list[vfs.DirContentItem]


@dataclass
class TreeEventNewItems(Generic[T]):
    """Triggered by `VfsTree.put_content`"""

    sender: T
    new_items: list[vfs.DirContentItem]


@dataclass
class TreeEventUpdatedItems(Generic[T]):
    """Triggered by `VfsTree.update_content`"""

    sender: T
    updated_items: Mapping[str, vfs.DirContentItem]


@dataclass
class TreeEventRemovedDirs(Generic[T]):
    """Triggered by `VfsTree.remove_dir`"""

    sender: T
    removed_dirs: list[str]


@dataclass
class TreeEventNewDirs(Generic[T]):
    """Triggered by `VfsTree.put_dir` and `VfsTree.create_dir`"""

    sender: T
    new_dirs: list[str]


TreeEventType = (
    TreeEventRemovedItems[T]
    | TreeEventNewItems[T]
    | TreeEventRemovedDirs[T]
    | TreeEventNewDirs[T]
    | TreeEventUpdatedItems[T]
)

from abc import abstractclassmethod, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Union

from tgmount import vfs


class VfsTreeProto(Protocol):
    pass


@dataclass
class TreeEventRemovedItems:
    """Triggered by `VfsTree.remove_content`"""

    update_path: str
    removed_items: list[vfs.DirContentItem]


@dataclass
class TreeEventNewItems:
    """Triggered by `VfsTree.put_content`"""

    update_path: str
    new_items: list[vfs.DirContentItem]


@dataclass
class TreeEventRemovedDirs:
    """Triggered by `VfsTree.remove_dir`"""

    removed_dirs: list[str]


@dataclass
class TreeEventNewDirs:
    """Triggered by `VfsTree.put_dir`"""

    new_dirs: list[str]


TreeEventType = (
    TreeEventRemovedItems | TreeEventNewItems | TreeEventRemovedDirs | TreeEventNewDirs
)

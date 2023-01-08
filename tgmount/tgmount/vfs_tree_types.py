from abc import abstractclassmethod, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Union

from tgmount import vfs


class VfsTreeProto(Protocol):
    pass


@dataclass
class TreeEventRemovedItems:
    """Items removed from `update_path`"""

    update_path: str
    removed_items: list[vfs.DirContentItem]


@dataclass
class TreeEventNewItems:
    """Items appeared at `update_path`"""

    update_path: str
    new_items: list[vfs.DirContentItem]


@dataclass
class TreeEventRemovedDirs:
    """Items appeared at `update_path`"""

    update_path: str
    removed_dirs: list[str]


@dataclass
class TreeEventNewDirs:
    update_path: str
    new_dirs: list[str]


TreeEventType = (
    TreeEventRemovedItems | TreeEventNewItems | TreeEventRemovedDirs | TreeEventNewDirs
)

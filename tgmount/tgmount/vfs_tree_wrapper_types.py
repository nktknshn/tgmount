from abc import abstractclassmethod, abstractmethod
from typing import Union

# from tgmount.tgmount.vfs_tree_types import TreeEventType
from tgmount import vfs


class VfsTreeWrapperProto:
    """Wraps a DirContent and events"""

    @abstractmethod
    def __init__(self, *args, **kwargs) -> None:
        ...

    @abstractclassmethod
    def from_config(self, *args, **kwargs) -> "VfsTreeWrapperProto":
        ...

    @abstractmethod
    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:
        ...

    @abstractmethod
    async def wrap_events(
        self, child: Union["VfsTreeDir", "VfsTree"], events: list["TreeEventType"]
    ) -> list["TreeEventType"]:
        ...

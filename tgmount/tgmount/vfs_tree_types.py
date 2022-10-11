from dataclasses import dataclass
from typing import Protocol, Union

from tgmount import vfs


class VfsTreeProto(Protocol):
    pass


@dataclass
class EventRemovedItems:
    update_path: str
    removed_items: list[vfs.DirContentItem]


@dataclass
class EventNewItems:
    update_path: str
    new_items: list[vfs.DirContentItem]


@dataclass
class EventRemovedDirs:
    update_path: str
    removed_dirs: list[str]


@dataclass
class EventNewDirs:
    update_path: str
    new_dirs: list[str]


TreeEventType = EventRemovedItems | EventNewItems | EventRemovedDirs | EventNewDirs


class Wrapper:
    def __init__(self) -> None:
        pass

    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:
        ...

    async def wrap_events(
        self, child: Union["VfsTreeDir", "VfsTree"], events: list[TreeEventType]
    ) -> list[TreeEventType]:
        ...


#
# class VfsTreeParentProto(Protocol):
#     @abstractmethod
#     async def remove_content(self, path: str, item: vfs.DirContentItem):
#         ...
#
#     @abstractmethod
#     async def put_content(
#         self,
#         content: Sequence[vfs.DirContentItem],
#         path: str = "/",
#         *,
#         overwright=False,
#     ):
#         ...
#
#     @abstractmethod
#     async def remove_dir(self, path: str):
#         ...
#
#     @abstractmethod
#     async def create_dir(self, path: str) -> "VfsTreeDir":
#         ...
#
#     @abstractmethod
#     async def get_content(self, subpath: str) -> list[vfs.DirContentItem]:
#         ...
#
#     @abstractmethod
#     async def get_dir(self, path: str) -> "VfsTreeDir":
#         ...
#
#     @abstractmethod
#     async def get_subdirs(self, path: str, *, recusrive=False) -> list["VfsTreeDir"]:
#         ...
#
#     @abstractmethod
#     async def put_dir(self, d: "VfsTreeDir") -> "VfsTreeDir":
#         ...
#
#     @abstractmethod
#     async def get_parent(self, path: str) -> Union["VfsTreeDir", "VfsTree"]:
#
#         ...
#
#     @abstractmethod
#     async def child_updated(
#         self, child: Union["VfsTreeDir", "VfsTree"], updates: list[UpdateType]
#     ):
#         ...

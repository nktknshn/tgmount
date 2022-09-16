from dataclasses import dataclass, field
import os
from abc import abstractmethod, abstractstaticmethod
from collections.abc import Awaitable, Callable
from typing import Iterable, Mapping, Optional, Protocol, TypeVar, Union

import telethon
from telethon.tl.custom import Message

from tgmount import tglog, vfs, fs
from tgmount.tgclient.message_source import Listener

from tgmount.util import none_fallback


logger = tglog.getLogger("VfsStructure")
logger.setLevel(tglog.TRACE)

PutEntity = Union[
    "VfsStructureProto",
    list[vfs.DirLike],
    list[vfs.FileLike],
]


class VfsStructureProto(Protocol):
    @abstractmethod
    async def list_content(
        self,
    ) -> tuple[dict[str, "VfsStructureProto"], list[vfs.DirContentItem],]:
        ...

    async def get_dir_content_list(self) -> list[vfs.DirContentItem]:
        dir_content_list = []

        subdirs, content = await self.list_content()

        dir_content_list.extend(content)

        for name, vs in subdirs.items():
            dir_content_list.append(vfs.vdir(name, await vs.get_dir_content_list()))

        return dir_content_list

    async def get_by_path(self, path: str | list[str]):
        if isinstance(path, str):
            path = vfs.napp(path, noslash=True)

        vs = self

        for p in path:
            (subdirs, content) = await vs.list_content()
            vs = subdirs[p]

        return vs


class VfsStructureBaseProto(VfsStructureProto):
    @abstractmethod
    async def list_content(
        self,
    ) -> tuple[dict[str, "VfsStructureProto"], list[vfs.DirContentItem],]:
        ...

    @abstractmethod
    async def put(self, path: str, vfs_structure: PutEntity, *, generate_event=False):
        """
        Method used by producer to create the initial state of the structure or add
        """
        ...

    @abstractmethod
    async def get_by_path(
        self, path: list[str] | str
    ) -> Optional["VfsStructureBaseProto"]:
        ...

    @abstractmethod
    async def put_subdir(
        self, dir_name: str, vfs_structure: "VfsStructureProto", *, generate_event=False
    ):
        ...

    @abstractmethod
    async def put_content(self, entity: PutEntity, *, generate_event=False):
        ...

    @abstractmethod
    async def remove_subitem(self, subitem: str):
        ...

    @abstractmethod
    async def remove_by_path(self, path: str):
        ...


def prepend_path_cur(parent_path: str):
    return lambda path: vfs.norm_path(parent_path + "/" + path, True)


@dataclass
class FsUpdate:
    update_dir_content: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    # new_files: dict[str, vfs.FileLike] = field(default_factory=dict)
    # new_dirs: dict[str, vfs.DirContentProto] = field(default_factory=dict)
    # removed_dir_contents: list[str] = field(default_factory=list)
    # removed_files: list[str] = field(default_factory=list)

    def prepend_paths(self, parent_path: str):
        _func = prepend_path_cur(parent_path)
        return FsUpdate(
            update_dir_content=list(map(_func, self.update_dir_content)),
        )

    def __repr__(self) -> str:
        return f"FsUpdate(update_dir_content={self.update_dir_content}, details={self.details})"


class VfsStructureProducerProto(Protocol):
    @abstractmethod
    def __init__(self, *args) -> None:
        ...

    @abstractmethod
    def get_vfs_structure(self) -> VfsStructureBaseProto:
        ...

    @abstractmethod
    async def produce_vfs_struct(self) -> VfsStructureProto:
        ...

    @abstractstaticmethod
    def from_config(
        root_producer: "VfsStructureProducerProto", resources, *args
    ) -> "VfsStructureProducerProto":
        ...

    async def on_child_update(
        self,
        subproducer: "VfsStructureProducerProto",
        update: FsUpdate,
    ):
        pass

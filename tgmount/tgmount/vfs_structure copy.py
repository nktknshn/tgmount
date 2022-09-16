import os
from abc import abstractmethod, abstractstaticmethod
from collections.abc import Awaitable, Callable
from typing import Iterable, Mapping, Optional, Protocol, TypeVar

import telethon
from telethon.tl.custom import Message

from tgmount import fs, tglog, vfs
from tgmount.tgclient.message_source import Subscribable
from tgmount.util import none_fallback

from .tgmount_root_producer_types import Set
from .vfs_structure_types import VfsStructureProtoBase

logger = tglog.getLogger("VfsStructure")
logger.setLevel(tglog.TRACE)

T = TypeVar("T")


def sets_difference(left: Set[T], right: Set[T]) -> tuple[Set[T], Set[T], Set[T]]:
    unique_left = left - right
    unique_right = right - left
    common = right.intersection(left)

    return unique_left, unique_right, common


class VfsStructureDirContent(vfs.DirContentProto):
    """DirContent wrapper. Returns state in VfsStructure"""

    def __init__(self, vfs_structure: "VfsStructure", path: str) -> None:
        self._vfs_structure = vfs_structure
        self._path = path

    async def readdir_func(self, handle, off: int):
        logger.info(f"ProducedContentDirContent({self._path}).readdir_func({off})")
        return await self._vfs_structure._get_by_path(self._path).readdir_func(
            handle, off
        )

    async def opendir_func(self):
        # logger.info(f"ProducedContentDirContent({self._path}).opendir_func()")
        return await self._vfs_structure._get_by_path(self._path).opendir_func()

    async def releasedir_func(self, handle):
        # logger.info(f"ProducedContentDirContent({self._path}).releasedir_func()")
        return await self._vfs_structure._get_by_path(self._path).releasedir_func(
            handle
        )


VfsStructureTree = dict[str, "VfsStructure" | "VfsStructureTree"]


class VfsStructure(Subscribable, VfsStructureProtoBase):
    """

    This structure is being produced and updated by VfsStructureProducer.

    the tree can be wrapped
    to turn zip files into dirs
    to remove empty dirs

    Stores updatable tree made of vfs entities.
    Every part of the tree is another VfsStructure providing its' own part of the tree.
    The class listens for updates from the child structures and update the compound tree.
    Updates are getting modified with corresponding paths and passed to the parent VFS.

    like:

    for message_by_user structure is gonna be constructed with calls:

    message_by_user.put('user1', user1_vfs_structure)
    message_by_user.put('user2', user2_vfs_structure)
    message_by_user.put('/', other_users_vfs_structure)

    and structure is gonna be:


    ZipsAsDirs(VfsStructure):
        init(vfs=VfsStructure)
            wrapped = vfs
            # this is how it will look like for the parent structure
            new = ...

        get_tree(self):
            # turn FileLike with zip into DirLike with DirContentProto of ZipTree
            self.vfs

        def update_vfs(update):
            # modify the update respectively to the new tree

    self._source_tree = {
        user1: VfsStructure1({
                all: VfsStructure({
                    message_666.txt: FileLike('message_666.txt'),
                    message_777.txt: FileLike('message_777.txt'),
                    zipfile1.zip: FileLike('zipfile1.zip'),
                }),

                docs: ZipsAsDirs(
                    wrapped = VfsStructure({
                        zipfile1.zip: FileLike('zipfile1.zip'),
                    }),
                    new = VfsStructure({
                        zipfile1: DirLike('zipfile1', unpacked_dir_content),
                    })
                ),
                images: VfsStructure({ ... }),
        }),
        user2: VfsStructure2({
                # VfsStructure
                all: { ... },

                # VfsStructure
                docs: { ... },

                # VfsStructure
                images: { ... },
        }),
        **VfsStructure3({
            message_1.txt: FileLike('message_1.txt'),
            message_2.txt: FileLike('message_2.txt'),
        }),
        **VfsStructure4({
            last_messages: VfsStructure({
                message_1.txt: FileLike('message_1.txt')
            })
        }),
    }

    self._by_path_vfs_stucture = {
        '/user1' : [VfsStructure1],
        '/user2' : [VfsStructure2],
        '/': [VfsStructure3, VfsStructure4]
    }
    """

    def __init__(self) -> None:
        super().__init__()

        # self._source_tree: VfsStructureTree = {}

        self._by_path_vfs_stucture: dict[str, list["VfsStructure"]] = {}
        self._by_vfs_stucture_path: dict["VfsStructure", str] = {}

        self._logger = logger

    async def put(
        self,
        path: str,
        structure: "VfsStructure",
        *,
        generate_event=False,
    ):

        structs = self._by_path_vfs_stucture.get(path, [])
        structs.append(structure)
        self._by_path_vfs_stucture[path] = structs

    def _get_path(self, path: str):
        pass

    async def get_tree(self) -> vfs.DirContentSourceMapping:
        pass

    def get_by_path(self, path: str):
        vfs.source_get_by_path(self._source_tree, path)

    def get_dir_content_by_path(self, path: str) -> vfs.DirContentProto:
        return VfsStructureDirContent(self, path)

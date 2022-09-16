import os
from abc import abstractmethod, abstractstaticmethod
from collections.abc import Awaitable, Callable
from typing import Iterable, Optional, Protocol, TypeVar

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
    """DirContent wrapper"""

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


class VfsStructure(Subscribable, VfsStructureProtoBase):
    """Updatable structure of VFS entities"""

    def __init__(self) -> None:
        super().__init__()

        self._by_path_content_dir: dict[str, vfs.DirContentProto] = {}
        # self._by_path_dirlikes: dict[str, list[vfs.DirLike]] = {}

        self._by_path_other_keys: dict[str, set[str]] = {}

        self._by_path_vfs_stucture: dict[str, "VfsStructure"] = {}
        self._by_vfs_stucture_path: dict["VfsStructure", str] = {}

        self._logger = logger

    async def update_vfs(self, update: fs.FileSystemOperationsUpdate):
        """Update the structure notifying listeners (parent vfs structure)"""
        # self._logger.info(
        #     f"VfsStructure.update(new_files={update.new_files}, removed_files={update.removed_files})"
        # )

        for path, content in update.update_dir_content.items():
            await self.put(path, content)

        for path, content in update.new_dirs.items():
            await self.put(path, content)

        for path in update.removed_dir_contents:
            await self.remove(path)

            # await self.put(path, content)

        await self.notify(update)

    async def on_subitem_update(
        self, sub_structure: "VfsStructure", update: fs.FileSystemOperationsUpdate
    ):
        self._logger.info(
            f"VfsStructure.on_subitem_update(new_files={list(update.new_files.keys())}, removed_files={list(update.removed_files.keys())})"
        )

        subvfs_path = self._by_vfs_stucture_path.get(sub_structure)

        if subvfs_path is None:
            self._logger.error(f"Missing subvfs in _by_vfs_stucture_path")
            return

        await self.notify(update.prepend_paths(subvfs_path))
        # for path, content in new_dir_content.items():
        #     await self.put(path, content)

    def get_root_dir_content(self):
        return self.get_dir_content_by_path("/")

    async def remove(self, path: str):
        del self._by_path_content_dir[path]

        if path in self._by_path_vfs_stucture:
            del self._by_vfs_stucture_path[self._by_path_vfs_stucture[path]]
            del self._by_path_vfs_stucture[path]

    async def put(
        self,
        path: str,
        dir_content: vfs.DirContentProto | VfsStructureProtoBase,
        *,
        generate_event=False,
    ):

        if not path.startswith("/"):
            path = "/" + path

        self._logger.info(f"put({path})")

        if not vfs.DirContentProto.guard(dir_content):
            self._by_path_vfs_stucture[path] = dir_content
            self._by_path_content_dir[path] = dir_content.get_root_dir_content()
            self._by_vfs_stucture_path[dir_content] = path

            dir_content.subscribe(self.on_subitem_update)

            if generate_event:
                await self.notify(
                    fs.FileSystemOperationsUpdate(
                        update_dir_content={"/": self.get_root_dir_content()},
                        new_dirs={path: self._by_path_content_dir[path]},
                    )
                )
        else:
            self._by_path_content_dir[path] = dir_content

            if generate_event:
                await self.notify(
                    fs.FileSystemOperationsUpdate(
                        update_dir_content={"/": self.get_root_dir_content()},
                    )
                )

        self._add_keys_from_path(path)

    def get_by_path(self, path: str):

        other_keys = self._by_path_other_keys.get(path, [])
        content = self._by_path_content_dir.get(path)

        return other_keys, content

    def walk_structure(self, path: str):
        other_keys, content = self.get_by_path(path)

        yield path, other_keys, content

        for key in other_keys:
            yield from self.walk_structure(os.path.join(path, key))

    def get_dir_content_by_path(self, path: str) -> vfs.DirContentProto:
        return VfsStructureDirContent(self, path)

    def _get_by_path(self, path: str) -> vfs.DirContentProto:
        # self._logger.info(f"get_by_path({path})")
        # self._logger.info(traceback.format_exc())

        vfs_structure = self._by_path_content_dir.get(path)
        other_keys = self._by_path_other_keys.get(path, [])

        other_keys_content = {}

        for key in other_keys:
            item_path = os.path.join(path, key)
            other_keys_content[key] = VfsStructureDirContent(
                vfs_structure=self, path=item_path
            )

        if vfs_structure is not None:
            return vfs.dir_content_extend(
                vfs_structure, vfs.dir_content_from_source(other_keys_content)
            )

        return vfs.dir_content_from_source(other_keys_content)

    def _add_keys_from_path(self, path: str):
        # self._logger.info(f"_add_keys_from_path({path})")

        if path != "/" and path != "":
            basename = os.path.basename(path)
            parent_path = os.path.dirname(path)

            if parent_path not in self._by_path_other_keys:
                self._by_path_other_keys[parent_path] = set()

            self._logger.trace(
                f"_add_keys_from_path({path}). adding {basename} to {parent_path}"
            )

            self._by_path_other_keys[parent_path].add(basename)
            self._add_keys_from_path(parent_path)

import os
from abc import abstractmethod, abstractstaticmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Iterable, Optional, Protocol, TypeVar, Union

import telethon
from telethon.tl.custom import Message

from tgmount import fs, tglog, vfs
from tgmount.tgclient.message_source import Subscribable
from tgmount.util import none_fallback

from .tgmount_root_producer_types import Set
from .vfs_structure_types import PutEntity, VfsStructureProtoBase

logger = tglog.getLogger("VfsStructure")
logger.setLevel(tglog.TRACE)

T = TypeVar("T")


class VfsStructureDirContent(vfs.DirContentProto):
    """DirContent wrapper"""

    def __init__(self, vfs_structure: "VfsStructure", path: str) -> None:
        self._vfs_structure = vfs_structure
        self._path = path

    async def readdir_func(self, handle, off: int):
        logger.info(f"ProducedContentDirContent({self._path}).readdir_func({off})")
        return await (await self._vfs_structure._get_by_path(self._path)).readdir_func(
            handle, off
        )

    async def opendir_func(self):
        # logger.info(f"ProducedContentDirContent({self._path}).opendir_func()")
        return await (await self._vfs_structure._get_by_path(self._path)).opendir_func()

    async def releasedir_func(self, handle):
        # logger.info(f"ProducedContentDirContent({self._path}).releasedir_func()")
        return await (
            await self._vfs_structure._get_by_path(self._path)
        ).releasedir_func(handle)


class VfsStructure(Subscribable, VfsStructureProtoBase):
    """Updatable structure of VFS entities"""

    def __init__(self) -> None:
        super().__init__()

        self._by_path_other_keys: dict[str, set[str]] = {}

        self._by_path_vfs_stucture: dict[str, list[PutEntity]] = {}
        self._by_vfs_stucture_path: dict["VfsStructureProto", str] = {}

        self._logger = logger

    async def put(self, path: str, vfs_structure: PutEntity, *, generate_event=False):
        path = vfs.norm_path(path, True)
        # self._logger.info(f"put({path})")

        self._put_by_path(path, vfs_structure)

        if isinstance(vfs_structure, VfsStructure):
            self._by_vfs_stucture_path[vfs_structure] = path
            vfs_structure.subscribe(self.on_subitem_update)

        if generate_event:
            await self.notify(
                fs.FileSystemOperationsUpdate(
                    update_dir_content={"/": await self.get_root_dir_content()},
                    new_dirs={path: await self.get_dir_content_by_path(path)},
                )
            )

        self._add_keys_from_path(path)

    async def get_tree(self):
        for path, other_keys, content in self.walk_structure():
            pass

    def get_by_path(self, path: str):

        other_keys = self._by_path_other_keys.get(path, set())
        vfs_struct = self._by_path_vfs_stucture.get(path)

        return other_keys, vfs_struct

    def walk_structure(self, path: str = "/", recursive=True):
        other_keys, content = self.get_by_path(path)

        yield path, other_keys, content

        if recursive:
            for key in other_keys:
                yield from self.walk_structure(os.path.join(path, key))

    async def update(
        self,
        removed_dir_contents: list[str],
        removed_files: list[str] = [],
        new_files: Mapping[str, vfs.FileLike] = {},
        # new_dirs: Mapping[str, "VfsStructure"] = {},
    ):
        """Update the structure notifying listeners (parent vfs structure)"""

        update = fs.FileSystemOperationsUpdate()

        for path in removed_dir_contents:
            path = vfs.norm_path(path, True)

            await self._remove(path)

            update.removed_dir_contents.append(path)
            update.update_dir_content[path] = await self.get_dir_content_by_path(path)

        for path in removed_files:
            path = vfs.norm_path(path, True)
            parent_path = os.path.dirname(path)

            await self._remove(path)

            update.removed_files.append(path)
            update.update_dir_content[parent_path] = await self.get_dir_content_by_path(
                parent_path
            )

        for path, file in new_files.items():
            path = vfs.norm_path(path, True)
            parent_path = os.path.dirname(path)

            await self.put(parent_path, [file])

            update.new_files[path] = file
            update.update_dir_content[parent_path] = await self.get_dir_content_by_path(
                parent_path
            )

            # await self.put(path, content)

        await self.notify(update)

    async def on_subitem_update(
        self, sub_structure: "VfsStructure", update: fs.FileSystemOperationsUpdate
    ):
        # self._logger.info(
        #     f"VfsStructure.on_subitem_update(new_files={list(update.new_files.keys())}, removed_files={list(update.removed_files)})"
        # )

        subvfs_path = self._by_vfs_stucture_path.get(sub_structure)

        if subvfs_path is None:
            self._logger.error(f"Missing subvfs in _by_vfs_stucture_path")
            return

        await self.notify(update.prepend_paths(subvfs_path))
        # for path, content in new_dir_content.items():
        #     await self.put(path, content)

    async def get_dir_content_by_path(self, path: str) -> vfs.DirContentProto:
        return VfsStructureDirContent(self, path)

    async def _remove(self, path: str):

        if path in self._by_path_vfs_stucture:
            vs = self._by_path_vfs_stucture[path]
            for v in vs:
                if isinstance(v, VfsStructure):
                    del self._by_vfs_stucture_path[v]

            del self._by_path_vfs_stucture[path]

    def _put_by_path(self, path: str, entity: PutEntity):
        vss = self._by_path_vfs_stucture.get(path, [])
        self._by_path_vfs_stucture[path] = [*vss, entity]

    async def _get_by_path(self, path: str) -> vfs.DirContentProto:
        # self._logger.info(f"get_by_path({path})")
        # self._logger.info(traceback.format_exc())

        vss = self._by_path_vfs_stucture.get(path, [])
        other_keys = self._by_path_other_keys.get(path, [])

        other_keys_content = {}

        for key in other_keys:
            item_path = os.path.join(path, key)
            other_keys_content[key] = VfsStructureDirContent(
                vfs_structure=self, path=item_path
            )

        dc = vfs.dir_content_from_source(other_keys_content)

        for vs in vss:
            if isinstance(vs, Iterable):
                dc = vfs.dir_content_extend(vfs.dir_content_from_source(vs), dc)
            else:
                dc = vfs.dir_content_extend(await vs.get_root_dir_content(), dc)

        return dc

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

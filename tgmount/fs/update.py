import os
from collections.abc import Callable
from dataclasses import dataclass, field

import pyfuse3

import tgmount.vfs as vfs
from tgmount.util import sets_difference
from tgmount.vfs.types.dir import DirLike
from .inode2 import InodesRegistry, RegistryItem
from .operations import FileSystemOperations
from .util import measure_time
from tgmount import tglog


def map_keys(
    mapper: Callable[[str], str],
    d: dict,
) -> dict:
    return {mapper(k): v for k, v in d.items()}


def prepend_path_cur(parent_path: str):
    return lambda path: vfs.norm_path(parent_path + "/" + path, True)


@dataclass
class FileSystemOperationsUpdate:
    update_dir_content: dict[str, vfs.DirContentProto] = field(default_factory=dict)
    new_files: dict[str, vfs.FileLike] = field(default_factory=dict)
    new_dirs: dict[str, vfs.DirLike | vfs.DirContentProto] = field(default_factory=dict)
    removed_dir_contents: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)

    def prepend_paths(self, parent_path: str):
        _prepend = prepend_path_cur(parent_path)
        return FileSystemOperationsUpdate(
            update_dir_content=map_keys(_prepend, self.update_dir_content),
            new_files=map_keys(_prepend, self.new_files),
            new_dirs=map_keys(_prepend, self.new_dirs),
            removed_dir_contents=list(map(_prepend, self.removed_dir_contents)),
            removed_files=list(map(_prepend, self.removed_files)),
        )

    def __repr__(self) -> str:
        return f"FileSystemOperationsUpdate(update_dir_content={list(self.update_dir_content.keys())}, new_files={list(self.new_files.keys())}, new_dirs={list(self.new_dirs.keys())}, removed_files={self.removed_files}, removed_dir_contents={self.removed_dir_contents})"


class FileSystemOperationsUpdatable(FileSystemOperations):
    def __init__(self, root: vfs.DirLike):
        super().__init__(root)

        self._removed_items = []

        # self._logger = tglog.getLogger("FileSystemOperationsUpdatable")

    async def _invalidate_children_by_path(
        self, path: list[bytes], parent_inode: int = InodesRegistry.ROOT_INODE
    ):
        """Recursively invalidates children"""

        item = self.inodes.get_by_path(path, parent_inode)

        if item is None:
            return

        kids = self.inodes.get_items_by_parent_dict(item.inode)

        if kids is None:
            return

        for k, v in kids.items():
            await self._invalidate_children_by_path([k], v.inode)
            pyfuse3.invalidate_entry_async(v.inode, k)

    async def update(self, update: FileSystemOperationsUpdate):
        for path, dir_like_or_content in update.update_dir_content.items():
            item = self.inodes.get_by_path(path)

            if item is None:
                self._logger.info(
                    f"on_update: update_dir_content: {path} is not in inodes"
                )
                continue

            if not isinstance(item.data.structure_item, vfs.DirLike):
                self._logger.error(
                    f"on_update: update_dir_content: {path} is not a folder"
                )
                continue

            item.data.structure_item.content = dir_like_or_content

        for path, filelike in update.new_files.items():
            parent_path = os.path.dirname(path)
            parent_item = self.inodes.get_by_path(parent_path)

            if parent_item is None:
                self._logger.info(
                    f"on_update: new_files: {parent_path} is not in inodes"
                )
                continue

            if not self.inodes.was_content_read(parent_item):
                continue

            self.add_subitem(filelike, parent_item.inode)

        for path, dir_like_or_content in update.new_dirs.items():
            parent_path = os.path.dirname(path)
            name = os.path.basename(path)
            parent_item = self.inodes.get_by_path(parent_path)

            if parent_item is None:
                self._logger.info(f"on_update: new_files: {path} is not in inodes")
                continue

            if not self.inodes.was_content_read(parent_item):
                continue

            vfs_item = (
                dir_like_or_content
                if isinstance(dir_like_or_content, vfs.DirLike)
                else vfs.DirLike(name, dir_like_or_content)
            )
            self.add_subitem(vfs_item, parent_item.inode)

        for path in update.removed_files:
            item = self.inodes.get_by_path(path)
            if item is None:
                self._logger.info(
                    f"on_update: update_dir_content: {path} is not in inodes"
                )
                continue
            if isinstance(item, RegistryItem):
                pyfuse3.invalidate_entry_async(
                    item.parent_inode, item.name, ignore_enoent=True
                )

            await self._remove_item(item)

        for path in update.removed_dir_contents:
            item = self.inodes.get_by_path(path)
            if item is None:
                self._logger.info(
                    f"on_update: update_dir_content: {path} is not in inodes"
                )
                continue

            if isinstance(item, RegistryItem):
                pyfuse3.invalidate_entry_async(
                    item.parent_inode, item.name, ignore_enoent=True
                )

            await self._remove_item(item)

    async def _remove_item(self, item: FileSystemOperations.FsRegistryItem):
        self._removed_items.append(item)
        return await self._remove_item_by_inode(item.inode)

    async def _remove_item_by_inode(self, inode: int):
        # async with self._update_lock:
        result = self.inodes.remove_item_with_children(inode)

        self._logger.info(
            f"_remove_item_by_inode({inode} ({self.inodes.get_item_path(inode)})) -> {result}"
        )
        return result

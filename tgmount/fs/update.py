import os
from dataclasses import dataclass, field

import pyfuse3

import tgmount.vfs as vfs
from tgmount.util.col import map_keys

from .inode import InodesRegistry, RegistryItem
from .operations import FileSystemOperations


def prepend_path_cur(parent_path: str):
    return lambda path: vfs.norm_path(parent_path + "/" + path, True)


@dataclass
class FileSystemOperationsUpdate:
    """Structure that represents an atomic update for FileSystemOperations"""

    new_files: dict[str, vfs.FileLike] = field(default_factory=dict)
    """ Add a list of vfs.FileLike at paths """

    new_dirs: dict[str, vfs.DirLike | vfs.DirContentProto] = field(default_factory=dict)
    """ Add a new directories. Keys are the paths of those directories, values are either `vfs.DirContent` or `vfs.DirLike`. If the value is `vfs.DirContent`, `vfs.DirLike` with a name sourced from the path is constructed, otherwise `vfs.DirLike` with its own name will be used and the directory name from the path will be ignored. """

    removed_dirs: list[str] = field(default_factory=list)
    """ List of directories to remove from FS """

    removed_files: list[str] = field(default_factory=list)
    """ List of files to remove from FS """

    # update_dir_content: dict[str, vfs.DirContentProto] = field(default_factory=dict)
    # """ Mapping of directories to update there  """

    def prepend_paths(self, parent_path: str):
        _prepend = prepend_path_cur(parent_path)
        return FileSystemOperationsUpdate(
            new_files=map_keys(_prepend, self.new_files),
            new_dirs=map_keys(_prepend, self.new_dirs),
            removed_files=list(map(_prepend, self.removed_files)),
            removed_dirs=list(map(_prepend, self.removed_dirs)),
            # update_dir_content=map_keys(_prepend, self.update_dir_content),
        )

    def __repr__(self) -> str:
        return f"FileSystemOperationsUpdate(new_files={list(self.new_files.keys())}, new_dirs={list(self.new_dirs.keys())}, removed_files={self.removed_files}, removed_dir_contents={self.removed_dirs})"


class FileSystemOperationsUpdatable(FileSystemOperations):
    def __init__(self, root: vfs.DirLike):
        super().__init__(root)

        self._removed_items = []

    async def update(self, update: FileSystemOperationsUpdate):

        for f in update.new_files:
            self.logger.info(f"New file: {f}")

        for path, filelike in update.new_files.items():
            parent_path = os.path.dirname(path)
            parent_item = self.inodes.get_by_path(parent_path)

            if parent_item is None:
                self.logger.debug(
                    f"on_update: new_files: {parent_path} is not in inodes"
                )
                continue

            # if content of the parent hasn't been accessed yet
            # skip adding subitems into inode registries
            if not self.inodes.was_content_read(parent_item):
                continue

            self.add_subitem(filelike, parent_item.inode)

        for path, dir_like_or_content in update.new_dirs.items():

            parent_path = os.path.dirname(path)
            name = os.path.basename(path)
            parent_item = self.inodes.get_by_path(parent_path)

            if parent_item is None:
                self.logger.debug(f"on_update: new_files: {path} is not in inodes")
                continue

            # if content of the parent hasn't been accessed yet
            # skip adding subitems into inode registries
            if not self.inodes.was_content_read(parent_item):
                continue

            vfs_item = (
                dir_like_or_content
                if isinstance(dir_like_or_content, vfs.DirLike)
                else vfs.DirLike(name, dir_like_or_content)
            )

            self.add_subitem(vfs_item, parent_item.inode)

        for path in update.removed_files:

            self.logger.info(f"Removed file: {path}")

            item = self.inodes.get_by_path(path)
            if item is None:
                self.logger.debug(
                    f"on_update: update_dir_content: {path} is not in inodes"
                )
                continue
            if isinstance(item, RegistryItem):
                pyfuse3.invalidate_entry_async(
                    item.parent_inode, item.name, ignore_enoent=True
                )

            await self._remove_item(item)

        for path in update.removed_dirs:
            item = self.inodes.get_by_path(path)

            if item is None:
                self.logger.debug(
                    f"on_update: update_dir_content: {path} is not in inodes"
                )
                continue

            if isinstance(item, RegistryItem):
                pyfuse3.invalidate_entry_async(
                    item.parent_inode, item.name, ignore_enoent=True
                )

            await self._remove_item(item)

        # for path, dir_like_or_content in update.update_dir_content.items():
        #     item = self.inodes.get_by_path(path)

        #     if item is None:
        #         self.logger.debug(
        #             f"on_update: update_dir_content: {path} is not in inodes"
        #         )
        #         continue

        #     if not isinstance(item.data.structure_item, vfs.DirLike):
        #         self.logger.error(
        #             f"on_update: update_dir_content: {path} is not a folder"
        #         )
        #         continue

        #     item.data.structure_item.content = dir_like_or_content

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

    def _remove_from_handles(self, item: RegistryItem):
        fhs = self._handles.get_by_item(item)

        if fhs is None:
            return

        self.logger.debug(f"_remove_from_handles({fhs})")

        for fh in fhs:
            self._handles.release_fh(fh)

    async def _remove_item(self, item: FileSystemOperations.FsRegistryItem):
        removed = await self._remove_item_by_inode(item.inode)

        if removed is None:
            return

        for i in removed:
            self._remove_from_handles(i)

    async def _remove_item_by_inode(self, inode: int):
        return self.inodes.remove_item_with_children(inode)

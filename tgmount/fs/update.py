import os
from typing import Iterable

from tgmount.vfs import compare
from .operations import FileSystemOperations
from .inode2 import InodesRegistry, RegistryItem

import tgmount.vfs as vfs
import pyfuse3
from .logger import logger, logger_update

from .util import measure_time


class FileSystemOperationsUpdatable(FileSystemOperations):
    def __init__(self, root: vfs.DirLike):
        super().__init__(root)

        self._removed_items = []

    def print_stats(self):
        print("inodes")
        print(self._inodes._inodes.keys())

        print("fhs")
        print(self._handles._fhs.keys())

    async def _invalidate_children_by_path(
        self, path: list[bytes], parent_inode: int = InodesRegistry.ROOT_INODE
    ):
        """Recursively invalidates children"""

        item = self.inodes.get_by_path(
            path,
            parent_inode,
        )

        if item is None:
            return

        kids = self.inodes.get_items_by_parent_dict(item.inode)

        if kids is None:
            return

        for k, v in kids.items():
            await self._invalidate_children_by_path([k], v.inode)
            pyfuse3.invalidate_entry_async(v.inode, k)

    async def _update_by_path(
        self,
        content: vfs.DirContent | vfs.FileContent,
        path: list[bytes] = [],
        parent_inode: int = InodesRegistry.ROOT_INODE,
    ):

        item = self.inodes.get_by_path(path, parent_inode)

        if item is None:
            return

        await self._invalidate_children_by_path(path, parent_inode)

        self.inodes.remove_item_with_children(item)

    def invalidate_all(self):
        pass
        # self.update_root(vfs.root())

    async def _remove_item(self, item: FileSystemOperations.FsRegistryItem):
        self._removed_items.append(item)
        return await self._remove_item_by_inode(item.inode)

    async def _remove_item_by_inode(self, inode: int):
        # async with self._update_lock:
        result = self.inodes.remove_item_with_children(inode)

        logger.info(
            f"_remove_item_by_inode({inode} ({self.inodes.get_item_path(inode)})) -> {result}"
        )
        return result

    async def _handle_dirlikes(
        self,
        path: list[str],
        old_fs_item: FileSystemOperations.FsRegistryItem,
        old_item: vfs.DirLike,
        new_item: vfs.DirLike,
    ):

        removed = set()
        updated = set()

        if not self.inodes.was_content_read(old_fs_item):
            old_fs_item.data.structure_item = new_item
            return removed, updated

        path_str = self.inodes.join_path(path)

        old_content = await vfs.dir_content_read_dict(old_item.content)
        new_content = await vfs.dir_content_read_dict(new_item.content)

        removed_keys = set(old_content.keys()) - set(new_content.keys())
        new_keys = set(new_content.keys()) - set(old_content.keys())
        common_keys = set(new_content.keys()).intersection(set(old_content.keys()))

        # logger.info(
        #     f"Updating folder content: {path_str}. removed_keys={removed_keys}, new_keys={new_keys}"
        # )

        for k in removed_keys:
            _item = self.inodes.get_child_item_by_name(k, old_fs_item.inode)

            if _item is None:
                logger.error(
                    f"Error while removing item: subitem named {k} was not found in {old_fs_item.inode} ({path_str})"
                )
                continue

            logger.info(f"Removing {k} ({_item.name})")

            _removed = await self._remove_item_by_inode(_item.inode)

            pyfuse3.invalidate_entry_async(
                old_fs_item.inode, _item.name, ignore_enoent=True
            )

            if _removed is None:
                logger.error(f"Inode {_item.inode} is not in registry.")
                continue

            removed = removed.union(_removed)

        for k in new_keys:
            new_fs_item = self.add_subitem(
                new_content[k], parent_inode=old_fs_item.inode
            )

        for k in common_keys:
            _item = self.inodes.get_child_item_by_name(k, old_fs_item.inode)

            if _item is None:
                logger.error(
                    f"Error while updating item: subitem named {k} was not found in {old_fs_item.inode} ({path_str})"
                )
                logger.error(
                    f"Removed items: {list(map(lambda item: item.name, self._removed_items))}"
                )
                continue

            if isinstance(_item.data.structure_item, vfs.DirLike):
                continue

            logger.debug(
                f"_handle_dirlikes: Updating structure item for subitem: {_item.data.structure_item.name}"
            )

            _item.data.structure_item = new_content[k]

            updated = updated.union({_item.inode})

        logger.debug(
            f"_handle_dirlikes: Updating structure item for: {old_fs_item.data.structure_item.name}"
        )
        old_fs_item.data.structure_item = new_item

        return removed, updated

    async def _handle_filelikes(
        self,
        fs_item: FileSystemOperations.FsRegistryItem,
        old_item: vfs.FileLike,
        new_item: vfs.FileLike,
    ):
        if old_item.extra != new_item.extra:
            pass
        logger.debug(
            f"_handle_filelikes: Updating structure item for: {fs_item.data.structure_item.name}"
        )
        fs_item.data.structure_item = new_item

    @measure_time(logger_func=logger.info)
    async def refresh_inodes(self, new_root: vfs.VfsRoot):

        logger_update.info(f"refresh_root2")

        removed = set()
        updated = set()

        for fs_item, path in self.inodes.get_items_with_paths_str():
            path_str = self.inodes.join_path(path)

            old_vfs_item = fs_item.data.structure_item

            if isinstance(fs_item.data.structure_item, vfs.FileLike):
                # file like items will be updated during its' parent dirs' comparison
                continue

            if fs_item.inode in removed:
                logger.info(
                    f"Inode {fs_item.inode} at {path_str} was removed. Skipping."
                )
                continue

            # if fs_item.inode in updated:
            #     logger.info(
            #         f"Inode {fs_item.inode} at {path_str} was already updated. Skipping."
            #     )
            #     continue

            # logger_update.info(f"Updating {fs_item.inode} ({path_str})")

            new_vfs_item = await vfs.dirlike_get_by_path_list(new_root, path)

            if new_vfs_item is None:
                logger_update.info(f"Missing {path_str} in new_root. Removing.")

                _removed = await self._remove_item_by_inode(fs_item.inode)

                if isinstance(fs_item, RegistryItem):
                    pyfuse3.invalidate_entry(fs_item.parent_inode, fs_item.name)

                if _removed is None:
                    logger.error(f"Inode {fs_item.inode} is not in registry.")
                    continue

                removed = removed.union(_removed)
                continue

            if isinstance(old_vfs_item, vfs.DirLike):
                if isinstance(new_vfs_item, vfs.DirLike):

                    _removed, _updated = await self._handle_dirlikes(
                        path, fs_item, old_vfs_item, new_vfs_item
                    )
                    removed = removed.union(_removed)
                    updated = removed.union(_updated)
                else:
                    logger.debug(
                        f"refresh_inodes: Updating structure item for: {fs_item.data.structure_item.name}"
                    )
                    fs_item.data.structure_item = new_vfs_item
            else:
                if isinstance(new_vfs_item, vfs.FileLike):
                    await self._handle_filelikes(fs_item, old_vfs_item, new_vfs_item)
                else:
                    logger.debug(
                        f"refresh_inodes: Updating structure item for: {fs_item.data.structure_item.name}"
                    )
                    fs_item.data.structure_item = new_vfs_item

        self._root = new_root

    async def refresh_root(self, new_root: vfs.VfsRoot):

        logger_update.info(f"refresh_root")

        for inode, path in self.inodes.get_inodes_with_paths_str():
            logger_update.debug(f"updating {inode} at {path}")

            new_item = await vfs.dirlike_get_by_path_list(new_root, path)

            if new_item is None:
                logger_update.error(f"missing {path} in new_root")
                continue

            fs_item = self.inodes.get_item_by_inode(inode)

            if fs_item is None:
                logger_update.info(f"missing {inode} in inodes")
                continue

            fs_item.data.structure_item = new_item

        self._root = new_root

    async def update_root(self, root: vfs.DirLike):
        await self.refresh_inodes(root)

    async def _update_root(self, root: vfs.DirLike):
        logger.debug(f"refresh_root")
        removed, new, changed = await vfs.compare_vfs_roots(self.vfs_root, root)

        if len(new) > 0:
            logger.info("new files:  ")
            for n in new:
                logger.info(os.path.join(*n.path, n.item.name))

        if len(removed) > 0:
            logger.info("removed")
            for n in removed:
                logger.info(os.path.join(*n.path, n.item.name))

        for n in new:
            path = self._str_to_bytes(n.path)
            folder = self.inodes.get_by_path(path)

            if folder is None:
                logger.error(f"Couldnt get item from inodes by path {path}")
                continue

            if not self.inodes.was_content_read(folder.inode):
                logger.error(f"Skipping {path}")
                continue

            pyfuse3.invalidate_inode(folder.inode)

            self.add_subitem(n.item, parent_inode=folder.inode)

        for r in removed:
            path = self._str_to_bytes(r.path)
            folder = self.inodes.get_by_path(path)

            if folder is None:
                continue

            if not self.inodes.was_content_read(folder.inode):
                continue

            self.remove_subitem(folder.inode, r.item.name)

            pyfuse3.invalidate_entry_async(
                folder.inode, self._str_to_bytes(r.item.name)
            )

        await self.refresh_root(root)

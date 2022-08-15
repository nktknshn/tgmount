from typing import Iterable
from .operations2 import FileSystemOperations
from .inode2 import InodesRegistry

import tgmount.vfs as vfs
import pyfuse3


class FileSystemOperationsUpdatable(FileSystemOperations):
    def __init__(self, root: vfs.DirLike):
        super().__init__(root)

    def print_stats(self):
        print("inodes")
        print(self._inodes._inodes.keys())

        print("fhs")
        print(self._handers._fhs.keys())

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

    async def update_root(self, root: vfs.DirLike):
        for inode in reversed(self.inodes.get_inodes()):
            # print(f"inode={inode}")
            kids = self.inodes.get_items_by_parent_dict(inode)

            if kids is None:
                continue

            for k, v in kids.items():
                # print(f"invalidate_entry({inode}, {k})")
                pyfuse3.invalidate_entry_async(inode, k)

        # pyfuse3.invalidate_inode(pyfuse3.ROOT_INODE)

        # for inode in self._inodes._inodes.keys():
        #     pyfuse3.invalidate_inode(inode)

        self._init_handers(self._handers._last_fh + 1)
        self._init_root(
            root,
            last_inode=self.inodes.last_inode,
        )

        print("update_root() done")

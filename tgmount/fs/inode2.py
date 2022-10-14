import logging
import os
from dataclasses import dataclass
from typing import (
    Dict,
    Generic,
    Optional,
    TypeVar,
    overload,
)

import pyfuse3

from tgmount import tglog
from .util import bytes_to_str, str_to_bytes

T = TypeVar("T")


@dataclass
class RegistryItem(Generic[T]):
    inode: int
    name: bytes
    data: T
    parent_inode: int

    def __hash__(self) -> int:
        return self.inode


@dataclass
class RegistryRoot(Generic[T]):
    inode: int
    data: T
    name = b"<root>"

    def __hash__(self) -> int:
        return self.inode


InodesRegistryItem = RegistryRoot[T] | RegistryItem[T]


class InodesRegistry(Generic[T]):
    ROOT_INODE: int = pyfuse3.ROOT_INODE

    def __init__(self, root_item: T, last_inode=None):

        self._logger = tglog.getLogger(f"InodesRegistry()")

        self._last_inode = (
            last_inode if last_inode is not None else InodesRegistry.ROOT_INODE
        )

        self._root_item = RegistryRoot(InodesRegistry.ROOT_INODE, root_item)

        self._inodes: Dict[int, RegistryItem[T]] = {
            # InodesRegistry.ROOT_INODE: root_item
        }

        self._dir_content_read: set[int] = set()

        # self._children_by_inode: Dict[int, Optional[dict[bytes, RegistryItem[T]]]] = {}

    def set_was_content_read(self, inode: int | InodesRegistryItem[T]):
        self._dir_content_read.add(self.get_inode(inode))

    def was_content_read(self, inode: int | InodesRegistryItem[T]):
        return self.get_inode(inode) in self._dir_content_read

    @property
    def last_inode(self):
        return self._last_inode

    def get_inodes(self):
        return list([self.get_root().inode, *self._inodes.keys()])

    def get_inodes_with_paths_str(self) -> list[tuple[int, list[str]]]:
        result = []

        for inode in self.get_inodes():
            path = self.get_item_path(inode)
            if path is not None:
                path = list(map(lambda el: el.decode("utf-8"), path))
            #     path = os.path.join(*path)
            result.append((inode, path))

        return result

    def get_items_with_paths_str(self) -> list[tuple[InodesRegistryItem[T], list[str]]]:
        result = []

        for item in self.get_items():
            path = self.get_item_path(item)

            if path is not None:
                path = bytes_to_str(path)
            #     path = os.path.join(*path)
            result.append((item, path))

        return result

    def get_root(self):
        return self._root_item

    def get_items(self):
        return list(self._inodes.values())

    def get_parent(self, inode: int | RegistryItem[T]):
        inode = self.get_inode(inode)
        item = self.get_item_by_inode(inode)

        if item is None:
            return

        if isinstance(item, RegistryRoot):
            raise ValueError("You cannot get parent for root")

        return self.get_item_by_inode(item.parent_inode)

    @staticmethod
    def get_inode(inode_or_item: int | InodesRegistryItem[T]) -> int:
        if isinstance(inode_or_item, RegistryItem) or isinstance(
            inode_or_item, RegistryRoot
        ):
            return inode_or_item.inode

        return inode_or_item

    @staticmethod
    def get_name(item: RegistryItem[T] | RegistryRoot[T]) -> bytes:
        if isinstance(item, RegistryRoot):
            return item.name

        return item.name

    def remove_item_with_children(
        self, inode_or_item: int | InodesRegistryItem[T]
    ) -> set[RegistryItem[T]] | None:

        inode = InodesRegistry.get_inode(inode_or_item)
        removed = set()
        item = self.get_item_by_inode(inode)

        if item is None:
            self._logger.error(
                f"remove_item_with_children: item with inode={inode} was not found."
            )
            return None

        if (subitems := self.get_item_children_inodes_recursively(item)) is not None:
            for _item in subitems:
                removed.add(_item)
                self._dir_content_read -= {_item}
                del self._inodes[_item.inode]

        removed.add(item)
        del self._inodes[item.inode]
        self._dir_content_read -= {item.inode}
        return removed

    def get_item_children_inodes_recursively(
        self, inode_or_item: int | RegistryItem[T] | RegistryRoot[T]
    ) -> Optional[set[RegistryItem[T]]]:
        result = set()
        children = self.get_items_by_parent(inode_or_item)

        if children is None:
            return None

        result = result.union(set(item for item in children))

        for subitem in children:
            _inodes = self.get_item_children_inodes_recursively(subitem)

            if _inodes is None:
                continue

            result = result.union(_inodes)

        return result

    def set_data_for_item(self, item: int | RegistryItem[T], data: T):
        inode = self.get_inode(item)
        self._inodes[inode].data = data

    def add_item_to_inodes(
        self,
        name: bytes,
        data: T,
        parent_inode: int | RegistryItem[T] = ROOT_INODE,
    ) -> RegistryItem[T]:

        inode = self._new_inode()

        item = self._inodes[inode] = RegistryItem(
            inode, name, data, self.get_inode(parent_inode)
        )

        return item

    def get_item_by_inode(
        self, inode: int
    ) -> Optional[RegistryItem[T] | RegistryRoot[T]]:

        if inode == InodesRegistry.ROOT_INODE:
            return self._root_item

        return self._inodes.get(inode)

    def get_child_item_by_name(
        self,
        name: bytes | str,
        parent_inode: int | RegistryItem[T] | RegistryRoot[T] = ROOT_INODE,
    ) -> Optional[RegistryItem[T] | RegistryRoot[T]]:

        if isinstance(name, str):
            name = str_to_bytes(name)

        parent_inode = self.get_inode(parent_inode)
        parent_item = self.get_item_by_inode(parent_inode)

        if parent_item is None:
            return

        child_items = self.get_items_by_parent_dict(parent_inode)

        # child_items_dict = self._items_dict_by_parent.get(parent_inode)

        if child_items is None:
            return

        if name == b".":
            return parent_item

        if name == b"..":
            if isinstance(parent_item, RegistryRoot):
                logging.error(
                    f"get_child_item_by_name('..', {parent_inode}). trying to go out of root item"
                )
                return None

            return self.get_parent(parent_inode)

        return child_items.get(name)

    def is_inode_exists(self, inode: int):
        return inode == self.ROOT_INODE or inode in self._inodes

    def get_items_by_parent(
        self,
        parent_inode: int | RegistryItem[T] | RegistryRoot[T] = ROOT_INODE,
    ):
        parent_inode = self.get_inode(parent_inode)

        if not self.is_inode_exists(parent_inode):
            return

        return [item for item in self.get_items() if item.parent_inode == parent_inode]

    def get_items_by_parent_dict(
        self,
        parent_inode: int | RegistryItem[T] = ROOT_INODE,
    ):
        items = self.get_items_by_parent(parent_inode)

        if items is None:
            return

        return {item.name: item for item in items}

    def get_item_path(
        self, inode: int | RegistryItem[T] | RegistryRoot[T]
    ) -> Optional[list[bytes]]:
        inode = self.get_inode(inode)
        item = self.get_item_by_inode(inode)

        if item is None:
            return

        if isinstance(item, RegistryRoot):
            return [b"/"]

        parent_item = self.get_parent(item)

        if parent_item is None:
            return

        parent_path = self.get_item_path(parent_item)

        if parent_path is None:
            return

        return [*parent_path, item.name]

    def get_by_path(
        self,
        path: list[bytes] | str,
        parent: int | RegistryItem[T] | RegistryRoot[T] = ROOT_INODE,
    ) -> Optional[RegistryItem[T] | RegistryRoot[T]]:

        if isinstance(path, str):
            path = str_to_bytes(path.split(os.path.sep))
            if len(path) > 0 and path[0] == b"":
                path = path[1:]

        parent_inode = self.get_inode(parent)
        parent_item = self.get_item_by_inode(parent_inode)

        if parent_item is None:
            return

        if path == b"" or path == [b""]:
            return parent_item

        if path == []:
            return parent_item

        if path == [b"/"]:
            return parent_item

        if path[0] == b"/":
            path = path[1:]

        [subitem_name, *rest] = path

        subitem = self.get_child_item_by_name(subitem_name, parent_item)

        if subitem is None:
            return

        if rest == []:
            return subitem

        return self.get_by_path(rest, subitem)

    @overload
    @staticmethod
    def join_path(path: list[str]) -> bytes:
        ...

    @overload
    @staticmethod
    def join_path(path: list[bytes]) -> bytes:
        ...

    @staticmethod
    def join_path(path) -> str | bytes:
        return os.path.join(*path)

    def _new_inode(self):
        # if self._last_inode is None:
        #     self._last_inode = pyfuse3.ROOT_INODE
        #     return self._last_inode

        self._last_inode += 1
        return self._last_inode

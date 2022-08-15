from typing import Optional, TypeVar
from tgmount.fs.inode2 import InodesRegistry, RegistryItem, RegistryRoot
from tgmount.vfs.util import nappb

T = TypeVar("T")


def test_inode_registry1():
    reg = InodesRegistry[str]("root")

    root_item = reg.get_root()
    item1 = reg.add_item_to_inodes(b"item1", "item1 content")
    subitem1 = reg.add_item_to_inodes(b"subitem1", "subitem1 content", item1.inode)
    subitem2 = reg.add_item_to_inodes(b"subitem2", "subitem2 content", item1)
    subsubitem1 = reg.add_item_to_inodes(
        b"subsubitem1", "subsubitem1 content", subitem1
    )

    assert item1 is not None

    assert item1.data == "item1 content"

    assert reg.get_item_by_inode(item1.inode) == item1
    assert reg.get_child_item_by_name(item1.name) == item1
    assert reg.get_child_item_by_name(subitem1.name, item1) == subitem1
    assert reg.get_child_item_by_name(b"none", item1) == None

    assert reg.get_items() == [item1, subitem1, subitem2, subsubitem1]
    assert reg.get_items_by_parent(item1) == [subitem1, subitem2]
    assert reg.get_items_by_parent(subitem1) == [subsubitem1]

    assert reg.get_parent(item1) == reg.get_root()
    assert reg.get_parent(subitem1) == item1
    assert reg.get_parent(subsubitem1) == subitem1

    assert reg.get_by_path(nappb("/")) == root_item
    assert reg.get_by_path(nappb("/item1")) == item1
    assert reg.get_by_path(nappb("/item1/")) == item1
    assert reg.get_by_path(nappb("/item1/subitem1")) == subitem1
    assert reg.get_by_path(nappb("/item1/subitem2")) == subitem2
    assert reg.get_by_path(nappb("/item1/subitem1/subsubitem1")) == subsubitem1

    assert reg.get_item_path(subsubitem1) == [
        b"/",
        item1.name,
        subitem1.name,
        subsubitem1.name,
    ]

    assert reg.get_item_path(item1) == [b"/", item1.name]

    assert reg.get_item_path(root_item) == [
        b"/",
    ]

from dataclasses import dataclass

from .dir_util import *


@dataclass
class RemovedItem:
    path: list[str]
    old_parent_item: DirLike
    new_parent_item: DirLike
    item: DirContentItem


@dataclass
class NewItem:
    path: list[str]
    old_parent_item: DirLike
    new_parent_item: DirLike
    item: DirContentItem


@dataclass
class ChangedItem:
    path: list[str]
    old_parent_item: DirLike
    new_parent_item: DirLike
    old_item: DirContentItem
    new_item: DirContentItem


async def compare_vfs_roots(
    root1: DirLike,
    root2: DirLike,
    # paths: list[list[str]] = [],
    path: list[str] = [],
):

    c1 = await dir_content_read_dict(root1.content)
    c2 = await dir_content_read_dict(root2.content)

    keys_in_c1 = set(c1.keys()) - set(c2.keys())
    keys_in_c2 = set(c2.keys()) - set(c1.keys())

    common_keys = set(c1.keys()).intersection(set(c2.keys()))

    removed_items = [RemovedItem(path, root1, root2, c1[k]) for k in keys_in_c1]
    new_items = [NewItem(path, root1, root2, c2[k]) for k in keys_in_c2]
    changed_items = []

    for k in common_keys:
        c1_item = c1[k]
        c2_item = c2[k]

        if isinstance(c1_item, DirLike):
            if isinstance(c2_item, DirLike):

                if c1_item.extra != c2_item.extra:
                    changed_items.append(
                        ChangedItem(path, root1, root2, c1_item, c2_item)
                    )
                    continue

                if c1_item.extra == c2_item.extra and c1_item.extra is not None:
                    continue

                _removed_items, _new_items, _changed_items = await compare_vfs_roots(
                    c1_item, c2_item, [*path, c1_item.name]
                )

                removed_items.extend(_removed_items)
                new_items.extend(_new_items)
                changed_items.extend(_changed_items)

            else:
                changed_items.append(ChangedItem(path, root1, root2, c1_item, c2_item))
        else:
            if isinstance(c2_item, FileLike):
                if c1_item.extra != c2_item.extra:
                    changed_items.append(
                        ChangedItem(path, root1, root2, c1_item, c2_item)
                    )
            else:
                changed_items.append(ChangedItem(path, root1, root2, c1_item, c2_item))

    return removed_items, new_items, changed_items

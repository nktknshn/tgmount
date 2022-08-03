import os
from typing import Iterable, List, Optional

from tgmount.vfs.types.dir import (
    DirContentItem,
    DirLike,
    is_directory,
)
from tgmount.vfs.util import norm_and_parse_path, napp
from .dir import get_dir_content_items


async def get_subitem_by_name(d: DirLike, name: str) -> Optional[DirContentItem]:
    handle = await d.content.opendir_func()
    items = await d.content.readdir_func(handle, 0)

    for item in items:
        if item.name == name:
            await d.content.releasedir_func(handle)
            return item

    await d.content.releasedir_func(handle)
    return None


async def get_by_path_list(d: DirLike, path: List[str]) -> Optional[DirContentItem]:

    if len(path) == 0:
        return d

    if path == ["/"]:
        return d

    if path[0] == "/":
        path = path[1:]

    subitem_name, *rest = path

    subitem = await get_subitem_by_name(d, subitem_name)

    if subitem is None:
        return None

    if len(rest) == 0:
        return subitem

    if not is_directory(subitem):
        return None

    return await get_by_path_list(subitem, rest)


async def get_by_path_str(d: DirLike, path: str) -> Optional[DirContentItem]:
    parsed_path = norm_and_parse_path(path)
    return await get_by_path_list(d, parsed_path)


async def list_dir_by_path(
    d: DirLike, path: list[str]
) -> Optional[Iterable[DirContentItem]]:
    """ """
    item = await get_by_path_list(d, path)

    if item is None:
        return None

    if not is_directory(item):
        return None

    items = await get_dir_content_items(item.content)

    return items

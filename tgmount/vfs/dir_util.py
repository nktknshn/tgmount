import functools
import os
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
)

from .file import file_content_from_file
from .types import FileLikeTree
from .types.dir import (
    DirContent,
    DirContentItem,
    DirContentProto,
    DirLike,
)
from .types.file import FileLike
from .util import lazy_list_from_thunk


def dir_content_from_fs(src_path: str) -> DirContent:
    """Use real fily system to create `DirContent`"""

    def get_content():
        content = []
        for file_name in os.listdir(src_path):
            full_path = os.path.join(src_path, file_name)

            if os.path.isdir(full_path):
                content.append(DirLike(file_name, dir_content_from_fs(full_path)))
            elif os.path.isfile(full_path):
                content.append(FileLike(file_name, file_content_from_file(full_path)))

        return content

    return DirContent(readdir_func=lazy_list_from_thunk(get_content))


def dir_content_map_items(
    mapper: Callable[[DirContentItem], DirContentItem],
    dir_content: DirContentProto,
) -> DirContent:
    async def f(handle, off):
        return map(mapper, await dir_content.readdir_func(handle, off))

    return DirContent(
        opendir_func=dir_content.opendir_func,
        releasedir_func=dir_content.releasedir_func,
        readdir_func=f,
    )


def dir_content_extend(
    content1: DirContentProto, content2: DirContentProto
) -> DirContent[list[DirContentItem]]:
    """Extends content1 with items from content2 returning `DirContent[list[DirContentItem]]`"""

    async def opendir_func():
        items1 = list(await dir_content_read(content1))
        items2 = list(await dir_content_read(content2))

        items1.extend(items2)

        return items1

    async def readdir_func(handle: list, off):
        return handle[off:]

    return DirContent(
        opendir_func=opendir_func,
        readdir_func=readdir_func,
    )


def dir_content_filter_items(
    filter: Callable[[DirContentItem], Awaitable[bool]],
    dir_content: DirContentProto,
) -> DirContent:
    async def f(handle, off):
        items = await dir_content.readdir_func(handle, off)
        res = []
        for item in items:
            if await filter(item):
                res.append(item)

        return res

    return DirContent(
        opendir_func=dir_content.opendir_func,
        releasedir_func=dir_content.releasedir_func,
        readdir_func=f,
    )


dir_content_map_f = lambda mapper: functools.partial(dir_content_map_items, mapper)


async def dir_content_to_tree(d: DirContentProto) -> FileLikeTree:
    """recursively consume `DirContentProto` returning `FileLikeTree`"""
    res: FileLikeTree = {}

    items = await dir_content_read(d)

    for item in items:
        if isinstance(item, DirLike):
            res[item.name] = await dir_content_to_tree(item.content)

        else:
            res[item.name] = item

    return res


async def file_like_tree_map(
    mapper: Callable[[FileLike], Awaitable[Any]], tree: FileLikeTree
):
    """map `FileLike` in FileLikeTree. Eg `file_like_tree_map({}, read_content_utf8)`"""
    res = {}

    for k, v in tree.items():
        if isinstance(v, FileLike):
            res[k] = await mapper(v)
        else:
            res[k] = await file_like_tree_map(mapper, v)

    return res


async def dir_content_read(content: DirContentProto) -> Iterable[DirContentItem]:
    """consume and return items from `content`. will open and release the `DirContentProto`"""
    h = await content.opendir_func()
    items = await content.readdir_func(h, 0)
    await content.releasedir_func(h)

    return items


async def dir_content_read_dict(
    content: DirContentProto,
) -> Mapping[str, DirContentItem]:
    return {item.name: item for item in await dir_content_read(content)}
